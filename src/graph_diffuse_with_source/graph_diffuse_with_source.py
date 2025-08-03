
"""
图传播算法工具包

此模块实现了一种基于图传播的节点相关性分析算法，该算法通过带有源头标识的信息传播机制，
计算图中节点间的相关性，并识别图的中心节点。算法核心实现在Gds(Graph Diffusion with Source)类中。

主要功能:
- 图初始化与参数设置
- 带有源头标识的消息传播
- 节点相关性计算
- 中心节点识别
- 结果可视化

依赖库:
- igraph: 用于图数据结构和操作
- json: 用于消息序列化
- math: 用于数学计算
- random: 用于随机操作
"""

# 导入所需库
import igraph as ig
import random
import json
import math

# 辅助函数
def merge_dicts_with_sum(list_of_dicts):
    """
    合并多个字典，将相同键的值相加

    参数:
        list_of_dicts: 字典列表

    返回:
        merged_dict: 合并后的字典，相同键的值已相加
    """
    # 初始化一个空字典用于存储结果
    merged_dict = {}
    
    # 遍历列表中的每个字典
    for d in list_of_dicts:
        # 遍历当前字典中的每个键值对
        for key, value in d.items():
            # 如果键已存在，则累加值；否则，直接添加键值对
            if key in merged_dict:
                merged_dict[key] += value
            else:
                merged_dict[key] = value
    
    return merged_dict

class Gds():
    """
    图传播算法核心类 (Graph Diffusion with Source)

    该类实现了带有源头标识的图传播算法，用于计算节点相关性和识别中心节点。
    """
    def __init__(self, G):
        """
        初始化Gds类

        参数:
            G: igraph.Graph对象，代表输入图
        """
        self.G=G
        self.df_vertexs=self.G.get_vertex_dataframe()
        self.df_vertexs.reset_index(inplace=True)
        # df_vertexs.head()
        self.id_nodeid_dict = self.df_vertexs.set_index('vertex ID')['node_id'].to_dict()
        self.nodeid_id_dict = {v: k for k, v in self.id_nodeid_dict.items()}
        self.G.vs["r_msg"] =json.dumps({})
        self.G.vs["buffer"] =json.dumps([])
        
        self.FADE =0.3
        vcount =self.G.vcount()
        if vcount>0:
            self.LIMIT =3*(1/vcount)
            self.MIN_SIZE = int(100/math.sqrt(vcount))
            self.MAX_SIZE = 6*self.MIN_SIZE
            self.DEFAULT_SIZE = 2*self.MIN_SIZE

        else:    
            self.LIMIT =0.03
            self.MIN_SIZE = 10
            self.MAX_SIZE = 20
            self.DEFAULT_SIZE = 2*self.MIN_SIZE
        # ig.plot(self.G)

    def add_one_node_ids(self, node_ids):
        """
        添加源节点并设置初始消息

        参数:
            node_ids: 源节点ID列表
        """
        for node_id in node_ids:
            vid = self.nodeid_id_dict[node_id]
            # for vid in vids:
                # node_id = node['id']
                # print(node_id)
            node =self.G.vs[vid]
            origin_msg = json.loads(self.G.vs[int(vid)]["r_msg"])
            # print(node_id,origin_msg)
            node_id = self.id_nodeid_dict[vid]
            add_msg ={str(node_id):1}
            origin_msg.update(add_msg)
            buffer =[]
            buffer.append(add_msg)
            buffer.append(origin_msg)
            merged_dict=merge_dicts_with_sum(buffer)
            
            node['r_msg']=json.dumps(merged_dict)
        self.normalize()    

                    

    def emit_to_buffer(self):
        """
        将所有节点的消息传播到邻居节点的缓冲区
        """
        # 清空所有节点的缓冲区
        self.G.vs["buffer"] = json.dumps([])
        vids = list(self.id_nodeid_dict.keys())
        for vid in vids:
            node = self.G.vs[vid]
            r_msg = json.loads(node["r_msg"])
            #  将源消息乘以衰减系数，计算需要传播的消息。
            faded_r_msg  = {key: value * self.FADE for key, value in r_msg.items()}
            neighbors = self.G.neighbors(vid)
            for neighbor in neighbors:
                buffer =json.loads(self.G.vs[neighbor]['buffer'])
                # 合并消息
                buffer.append(faded_r_msg)
                # 存入缓冲区
                self.G.vs[neighbor]['buffer']=json.dumps(buffer)

            node_id = self.id_nodeid_dict[vid]
            # 清空节点消息，将源节点输出权重设置为0。
            
            r_msg.update({str(node_id):0})
   
            self.G.vs[vid]['r_msg']=json.dumps(r_msg)
                
            
    def merge_from_buffer(self):
        """
        从缓冲区合并消息到节点
        """
        vids = list(self.id_nodeid_dict.keys())
        for vid in vids:
            node = self.G.vs[vid]
            r_msg = json.loads(node["r_msg"])
            buffer =json.loads(node['buffer'])
            buffer.append(r_msg)
            # print(buffer)
            merged_dict=merge_dicts_with_sum(buffer)
            filtered_dict = {key: value for key, value in merged_dict.items() if value >= self.LIMIT}
            node['r_msg']=json.dumps(filtered_dict)
        self.normalize()
        self.G.vs["buffer"] =json.dumps([])
            
        
        
                        
    def normalize(self):
        """
        归一化节点消息，确保每个节点的消息权重总和为1
        """
        vids = list(self.id_nodeid_dict.keys())
        for vid in vids:
            node = self.G.vs[vid]
            r_msg = json.loads(node["r_msg"])
            total = sum(r_msg.values())
            if total >0:
                for key in r_msg.keys():
                    r_msg[key] = r_msg[key]/total
                node["r_msg"] = json.dumps(r_msg)
            else:
                node_id=self.id_nodeid_dict[vid]
                node["r_msg"] = json.dumps({str(node_id):1})

    def show_nodes(self, node_data):
        """
        可视化节点数据，根据关联度设置节点颜色和大小

        参数:
            node_data: 包含节点ID和关联度的元组列表
        """
        # 可以对关联度进行缩放，使节点大小在合适范围内
        min_size = self.MIN_SIZE
        max_size = self.MAX_SIZE
        self.G.vs()['color']='red'
        self.G.vs()['size']=self.DEFAULT_SIZE
        node_ids = [v[0] for v in node_data]
        
        for v in node_data:
            # node_id=int(v[0])
            vid = self.nodeid_id_dict[v[0]]
            # vid = self.nodeid_id_dict[node_id]
            s = v[1]
            scaled_size=int((max_size - min_size) * s*5)
            node = self.G.vs[vid]
            node['color']='green'
            # r_msg = json.loads(node["r_msg"])
            # print(r_msg)
            
        # 设置节点大小属性
            node['size']=scaled_size
            
    def show_central(self):
        """
        计算并返回图中的中心节点

        返回:
            filtered_dict: 包含中心节点ID和归一化关联度的字典
        """
        vids = list(self.id_nodeid_dict.keys())
        buffer = []
        for vid in vids:
            node = self.G.vs[vid]
            r_msg = json.loads(node["r_msg"])
            buffer.append(r_msg)
        
        
                
        merged_dict=merge_dicts_with_sum(buffer)
        # normalize merged_dict
        total = sum(merged_dict.values())
        if total >0:
            factor=1/total
            merged_dict=  {key: (value*factor) for key, value in merged_dict.items()}
            filtered_dict = {key: value for key, value in merged_dict.items() if value >= self.LIMIT}
        else:
            filtered_dict = merged_dict
        return filtered_dict
        
        
        
        
        
         
