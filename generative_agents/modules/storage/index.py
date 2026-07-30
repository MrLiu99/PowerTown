"""generative_agents.storage.index"""

import os
import time
import traceback
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.indices.vector_store.retrievers import VectorIndexRetriever
from llama_index.core.schema import TextNode
from llama_index import core as index_core
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings

from modules import utils


class LlamaIndex:
    def __init__(self, embedding_config, path=None):
        """
        embedding_config: 嵌入模型配置
        path: 持久化存储路径
        """
        self._config = {"max_nodes": 0} # 记录节点总数
        # 1. 根据配置选择嵌入模型
        if embedding_config["provider"] == "hugging_face":
            embed_model = HuggingFaceEmbedding(model_name=embedding_config["model"])
        elif embedding_config["provider"] == "ollama":
            embed_model = OllamaEmbedding(
                model_name=embedding_config["model"],
                base_url=embedding_config["base_url"],
                ollama_additional_kwargs={"mirostat": 0},
            )
        elif embedding_config["provider"] == "openai":
            embed_model = OpenAIEmbedding(
                model_name=embedding_config["model"],
                api_base=embedding_config["base_url"],
                api_key=embedding_config["api_key"],
            )
        else:
            raise NotImplementedError(
                "embedding provider {} is not supported".format(embedding_config["provider"])
            )
        # 2. 配置全局设置
        Settings.embed_model = embed_model
        Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)# 文本块大小、重叠部分
        Settings.num_output = 1024 #输出token数
        Settings.context_window = 4096 # 上下文窗口
         # 3. 加载或创建索引
        if path and os.path.exists(path):
            # 从磁盘加载已有索引
            self._index = index_core.load_index_from_storage(
                index_core.StorageContext.from_defaults(persist_dir=path),
                show_progress=True,
            )
            self._config = utils.load_dict(os.path.join(path, "index_config.json"))
        else:
            # 创建新的空索引
            self._index = index_core.VectorStoreIndex([], show_progress=True)
        self._path = path

    # 向索引中添加一个新节点
    def add_node(
        self,
        text,
        metadata=None,
        exclude_llm_keys=None,
        exclude_embedding_keys=None,
        id=None,
    ):
        """
        添加一条记忆到向量数据库
        text: 记忆的文本内容
        metadata: 元数据(时间、地点、重要性等)
        exclude_llm_keys: LLM不需要看到的metadata字段
        exclude_embedding_keys: 不参与向量化的metadata字段
        id: 节点ID(可选)
        """
        while True:
            try:
                metadata = metadata or {}
                # 默认所有metadata都不给LLM和Embedding看
                exclude_llm_keys = exclude_llm_keys or list(metadata.keys())
                exclude_embedding_keys = exclude_embedding_keys or list(metadata.keys())
                # 生成唯一ID
                id = id or "node_" + str(self._config["max_nodes"])
                self._config["max_nodes"] += 1
                # 创建节点
                node = TextNode(
                    text=text,
                    id_=id,
                    metadata=metadata,
                    excluded_llm_metadata_keys=exclude_llm_keys,
                    excluded_embed_metadata_keys=exclude_embedding_keys,
                )
                self._index.insert_nodes([node]) # 插入索引(自动计算embedding)
                return node
            except Exception as e:
                print(f"LlamaIndex.add_node() caused an error: {e}")
                traceback.print_exc()
                time.sleep(5)
    # 检查索引中是否存在某个节点
    def has_node(self, node_id):
        return node_id in self._index.docstore.docs
    # 根据节点ID查找节点
    def find_node(self, node_id):
        return self._index.docstore.docs[node_id]
    # 获取所有节点，支持过滤
    def get_nodes(self, filter=None):
        def _check(node):
            if not filter:
                return True
            return filter(node)

        return [n for n in self._index.docstore.docs.values() if _check(n)]
    # 删除指定节点
    def remove_nodes(self, node_ids, delete_from_docstore=True):
        self._index.delete_nodes(node_ids, delete_from_docstore=delete_from_docstore)
    # 清理过期节点
    def cleanup(self):
        now, remove_ids = utils.get_timer().get_date(), []
        for node_id, node in self._index.docstore.docs.items():
            create = utils.to_date(node.metadata["create"])
            expire = utils.to_date(node.metadata["expire"])
            if create > now or expire < now:
                remove_ids.append(node_id)
        self.remove_nodes(remove_ids)
        return remove_ids
    
    # 基于语义相似度检索记忆
    def retrieve(
        self,
        text,                    # 查询文本
        similarity_top_k=5,      # 返回top-k个最相似的
        filters=None,            # 元数据过滤器
        node_ids=None,           # 限定在这些节点中搜索
        retriever_creator=None,  # 自定义检索器
    ):
        try:
            retriever_creator = retriever_creator or VectorIndexRetriever
            # 创建检索器
            return retriever_creator(
                self._index,
                similarity_top_k=similarity_top_k,
                filters=filters,
                node_ids=node_ids,
            ).retrieve(text) # 执行检索
        except Exception as e:
            # print(f"LlamaIndex.retrieve() caused an error: {e}")
            return []
    # 基于语义相似度查询记忆，并生成回答
    def query(
        self,
        text,
        similarity_top_k=5,
        text_qa_template=None,
        refine_template=None,
        filters=None,
        query_creator=None,
    ):
        kwargs = {
            "similarity_top_k": similarity_top_k,
            "text_qa_template": text_qa_template,
            "refine_template": refine_template,
            "filters": filters,
        }
        while True:
            try:
                if query_creator:
                    query_engine = query_creator(retriever=self._index.as_retriever(**kwargs))
                else:
                    query_engine = self._index.as_query_engine(**kwargs)
                return query_engine.query(text)
            except Exception as e:
                print(f"LlamaIndex.query() caused an error: {e}")
                time.sleep(5)
    # 保存索引到磁盘
    def save(self, path=None):
        path = path or self._path
        self._index.storage_context.persist(path)
        utils.save_dict(self._config, os.path.join(path, "index_config.json"))

    @property
    def nodes_num(self):
        return len(self._index.docstore.docs)
