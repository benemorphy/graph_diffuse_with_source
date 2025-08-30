
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
        self.node_ids =self.df_vertexs['node_id'].tolist()

        self.id_nodeid_dict = self.df_vertexs.set_index('vertex ID')['node_id'].to_dict()
        self.nodeid_id_dict = {v: k for k, v in self.id_nodeid_dict.items()}
        self.nodeid_buffer_dict = {k:json.dumps([]) for k, v in self.nodeid_id_dict.items()}
        self.nodeid_msg_dict = {k: json.dumps({})for k, v in self.nodeid_id_dict.items()}

        
        self.FADE =0.3
        vcount =self.G.vcount()
        if vcount>3:
            self.LIMIT =0.3*(1/math.sqrt(vcount))

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
            try:

                origin_msg = json.loads(self.nodeid_msg_dict[node_id])
                # print('origin_msg',origin_msg)

                add_msg ={str(node_id):1}
                origin_msg.update(add_msg)
                # print('origin_msg after',origin_msg)

                buffer =[]
                buffer.append(add_msg)
                buffer.append(origin_msg)
                # print('buffer',buffer)
                merged_dict=merge_dicts_with_sum(buffer)
                # print('merged_dict',merged_dict)
                self.nodeid_msg_dict[node_id]=json.dumps(merged_dict)
                self.normalize_node_id(node_id)
            except:
                pass
        # self.normalize()    

    def negative_add_one_node_ids(self, node_ids):
        """
        添加源节点并设置初始消息

        参数:
            node_ids: 源节点ID列表
        """
        negative_node_ids =[v for v in self.node_ids if v not in node_ids]
        
        for node_id in negative_node_ids:
            try:

                origin_msg = json.loads(self.nodeid_msg_dict[node_id])
                add_msg ={str(node_id):1}
                origin_msg.update(add_msg)
                buffer =[]
                buffer.append(add_msg)
                buffer.append(origin_msg)
                merged_dict=merge_dicts_with_sum(buffer)
                
                self.nodeid_msg_dict[node_id]=json.dumps(merged_dict)
                self.normalize_node_id(node_id)
            except:
                pass
              

    def emit_to_buffer(self,node_ids):
        """
        将所有节点的消息传播到邻居节点的缓冲区
        """
        # 清空所有节点的缓冲区
        # self.nodeid_buffer_dict = {v: (json.dumps([])) for k, v in self.id_nodeid_dict.items()}
        # node_ids = list(self.nodeid_id_dict.keys())
        for node_id in node_ids:
            # node = self.G.vs[vid]
            r_msg = json.loads(self.nodeid_msg_dict[node_id])
            # print('before r_msg',node_id,r_msg)
            
            #  将源消息乘以衰减系数，计算需要传播的消息。
            faded_r_msg  = {key: value * self.FADE for key, value in r_msg.items()}
            # print('after r_msg',node_id,faded_r_msg)
            
            # 传播到邻居节点
            vid=self.nodeid_id_dict[node_id]
            neighbors = self.G.neighbors(vid)
            for neighbor in neighbors:
                neighbor_id = self.id_nodeid_dict[neighbor]
                buffer =json.loads(self.nodeid_buffer_dict[neighbor_id])
                # print('before',neighbor_id,buffer)


                # 合并消息
                buffer.append(faded_r_msg)
                # print(neighbor_id,buffer)


                # 存入缓冲区
                self.nodeid_buffer_dict[neighbor_id]=json.dumps(buffer)
            # 清空节点消息，将源节点输出权重设置为0。         
            r_msg={node_id:0}
            self.nodeid_msg_dict[node_id]=json.dumps(r_msg)
                    
    def merge_from_buffer(self):
        """
        从缓冲区合并消息到节点
        """
        node_ids = list(self.nodeid_id_dict.keys())
        for node_id in node_ids:
            try:

                r_msg = json.loads(self.nodeid_msg_dict[node_id])
                buffer =json.loads(self.nodeid_buffer_dict[node_id])
                buffer.append(r_msg)
                # print(buffer)
                merged_dict=merge_dicts_with_sum(buffer)
                # print(merged_dict)
                filtered_dict = {key: value for key, value in merged_dict.items() if value >= self.LIMIT}
                # print(filtered_dict)
                total = sum(filtered_dict.values())
                update_msg ={node_id:total}
                filtered_dict.update(update_msg)
                self.nodeid_msg_dict[node_id]=json.dumps(filtered_dict)
                self.normalize_node_id(node_id)

                # 清空缓冲区

                
            except:
                pass

            self.normalize_node_id(node_id)
        for node_id in node_ids:
            self.nodeid_buffer_dict[node_id]='[]'


    def normalize(self):
        """
        归一化节点消息，确保每个节点的消息权重总和为1
        """
        node_ids = list(self.nodeid_id_dict.keys())
        for node_id in node_ids:
            r_msg = json.loads(self.nodeid_msg_dict[node_id])
            total = sum(r_msg.values())
            if total >0:
                scale =1/total
                for key in r_msg.keys():
                    r_msg[key] = r_msg[key]*scale
                self.nodeid_msg_dict[node_id] = json.dumps(r_msg)
            else:
                self.nodeid_msg_dict[node_id] = json.dumps({str(node_id):0})

    def normalize_node_id(self,node_id):
        """
        归一化节点消息，确保每个节点的消息权重总和为1
        """

        # for node_id in node_ids:
        r_msg = json.loads(self.nodeid_msg_dict[node_id])
        total = sum(r_msg.values())
        if total >0:
            scale =1/total
            for key in r_msg.keys():
                r_msg[key] = r_msg[key]*scale
            self.nodeid_msg_dict[node_id] = json.dumps(r_msg)
        else:
            self.nodeid_msg_dict[node_id] = json.dumps({str(node_id):0})
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

        # 设置节点大小属性
            node['size']=scaled_size
    def zerofy_all(self):
        self.nodeid_msg_dict = {k: json.dumps({})for k, v in self.nodeid_id_dict.items()}  
            
    def neg_key_nodes(self,node_ids):
        """

        参数:
            node_ids: 包含节点ID的列表
        """
        self.zerofy_all()
        
    # 找到所有节点
        nodeids_all = list(self.nodeid_id_dict.keys())
        # 节点之外的其他节点赋值1
        self.negative_add_one_node_ids(node_ids)
        # 节点之外的节点扩散
        self.emit_to_buffer(nodeids_all)
        self.merge_from_buffer()   
        # 找出节点的消息，并且合并
        buffer =[]
        for node_id in node_ids:
            r_msg = json.loads(self.nodeid_msg_dict[node_id])
            buffer.append(r_msg)
        # 合并消息
        merged_dict = merge_dicts_with_sum(buffer)
        total = sum(merged_dict.values())
        if total >0:
            factor=1/total
            factor_limit =2*(1/self.G.vcount())

            merged_dict=  {key: (value*factor) for key, value in merged_dict.items()}
            filtered_dict = {key: value for key, value in merged_dict.items() if value >= factor_limit}
        else:
            filtered_dict = merged_dict

        return filtered_dict
        
    def pos_key_nodes(self,node_ids):
        """

        参数:
            node_ids: 包含节点ID的列表
        """
        self.zerofy_all()
        nodeids_all = list(self.nodeid_id_dict.keys())
        self.add_one_node_ids(node_ids)
        self.emit_to_buffer(nodeids_all)
        self.merge_from_buffer()        
        buffer =[]
        for node_id in nodeids_all:
            r_msg = json.loads(self.nodeid_msg_dict[node_id])
            buffer.append(r_msg)
        # 合并消息
        merged_dict = merge_dicts_with_sum(buffer)
        total = sum(merged_dict.values())
        if total >0:
            factor=1/total
            factor_limit =2*(1/self.G.vcount())

            merged_dict=  {key: (value*factor) for key, value in merged_dict.items()}
            filtered_dict = {key: value for key, value in merged_dict.items() if value >= factor_limit}
        else:
            filtered_dict = merged_dict

        return filtered_dict
    def show_central(self):
        """
        计算并返回图中的中心节点

        返回:
            filtered_dict: 包含中心节点ID和归一化关联度的字典
        """
        vids = list(self.id_nodeid_dict.keys())
        buffer = []
        for vid in vids:
            node_id = self.id_nodeid_dict[vid]

            r_msg = json.loads(self.nodeid_msg_dict[node_id])

            buffer.append(r_msg)
        
        
                
        merged_dict=merge_dicts_with_sum(buffer)
        # normalize merged_dict
        total = sum(merged_dict.values())
        if total >0:
            factor=1/total
            factor_limit =2*(1/self.G.vcount())


            merged_dict=  {key: (value*factor) for key, value in merged_dict.items()}
            filtered_dict = {key: value for key, value in merged_dict.items() if value >= factor_limit}
        else:
            filtered_dict = merged_dict
        return filtered_dict
        
        
        
        
        
         
