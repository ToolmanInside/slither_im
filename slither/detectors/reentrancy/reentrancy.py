""""
    Re-entrancy detection

    Based on heuristics, it may lead to FP and FN
    Iterate over all the nodes of the graph until reaching a fixpoint
"""

from slither.core.cfg.node import NodeType
from slither.core.declarations import Function, SolidityFunction
from slither.core.expressions import UnaryOperation, UnaryOperationType
from slither.detectors.abstract_detector import (AbstractDetector,
                                                 DetectorClassification)
from slither.visitors.expression.export_values import ExportValues
from slither.slithir.operations import (HighLevelCall, LowLevelCall,
                                        LibraryCall,
                                        Send, Transfer)

class Reentrancy(AbstractDetector):
    ARGUMENT = 'reentrancy'
    HELP = 'Reentrancy vulnerabilities'
    IMPACT = DetectorClassification.HIGH
    CONFIDENCE = DetectorClassification.MEDIUM

    WIKI = 'https://github.com/trailofbits/slither/wiki/Vulnerabilities-Description#reentrancy-vulnerabilities'

    key = 'REENTRANCY'

    @staticmethod
    def _can_callback(node):
        """
            Detect if the node contains a call that can
            be used to re-entrance

            Consider as valid target:
            - low level call
            - high level call

            Do not consider Send/Transfer as there is not enough gas
        """
        for ir in node.irs:
            if isinstance(ir, LowLevelCall):
                return True
            if isinstance(ir, HighLevelCall) and not isinstance(ir, LibraryCall):
                return True
        return False

    @staticmethod
    def _can_send_eth(node):
        """
            Detect if the node can send eth
        """
        for ir in node.irs:
            if isinstance(ir, (HighLevelCall, LowLevelCall, Transfer, Send)):
                if ir.call_value:
                    return True
        return False

    def _check_on_call_returned(self, node):
        """
            Check if the node is a condtional node where
            there is an external call checked
            Heuristic:
                - The call is a IF node
                - It contains a, external call
                - The condition is the negation (!)

            This will work only on naive implementation
        """
        return isinstance(node.expression, UnaryOperation)\
            and node.expression.type == UnaryOperationType.BANG

    def _explore(self, node, visited):#node=function.entry_point
        """
            Explore the CFG and look for re-entrancy
            Heuristic: There is a re-entrancy if a state variable is written
                        after an external call“这个地方的FP就会比较高”

            node.context will contains the external calls executed  执行的外部调用
            It contains the calls executed in father nodes   意思是node.context这个属性里面存放fathers的节点的外部调用

            if node.context is not empty, and variables are written, a re-entrancy is possible。有外部调用，变量被写。就有可能可重入
        """
        if node in visited:
            return
        visited = visited + [node]

        # First we add the external calls executed in previous nodes
        # send_eth returns the list of calls sending value
        # calls returns the list of calls that can callback
        # read returns the variable read
        fathers_context = {'send_eth':[], 'calls':[], 'read':[]}  #爸爸们的外部调用

        for father in node.fathers:
            if self.key in father.context:   #sef.key = 'REENTRANCY'，#father.context是一个字典如果'REENTRANCY'是字典里面的一个key
                fathers_context['send_eth'] += father.context[self.key]['send_eth']
                fathers_context['calls'] += father.context[self.key]['calls']
                fathers_context['read'] += father.context[self.key]['read']

        # Exclude path that dont bring further information
        if node in self.visited_all_paths: #self.visited_all_paths在本文件第173行初始化self.visited_all_paths={}
            if all(call in self.visited_all_paths[node]['calls'] for call in fathers_context['calls']):
                if all(send in self.visited_all_paths[node]['send_eth'] for send in fathers_context['send_eth']):
                    if all(read in self.visited_all_paths[node]['read'] for read in fathers_context['read']):
                        return
        else:
            self.visited_all_paths[node] = {'send_eth':[], 'calls':[], 'read':[]}

        self.visited_all_paths[node]['send_eth'] = list(set(self.visited_all_paths[node]['send_eth'] + fathers_context['send_eth']))
        self.visited_all_paths[node]['calls'] = list(set(self.visited_all_paths[node]['calls'] + fathers_context['calls']))
        self.visited_all_paths[node]['read'] = list(set(self.visited_all_paths[node]['read'] + fathers_context['read']))

        node.context[self.key] = fathers_context  #fathers_context = {'send_eth':[], 'calls':[], 'read':[]}，self.key= key = 'REENTRANCY'

        contains_call = False
        if self._can_callback(node):# 检测node是否包含一个外部调用，这个外部调用可能被利用来reentrancy  本文件第29行，，规则看一下
            node.context[self.key]['calls'] = list(set(node.context[self.key]['calls'] + [node]))#从这行可以看出node.context[self.key]['calls']里边装的是node对象
            contains_call = True
        if self._can_send_eth(node):# Detect if the node can send eth   本文件48行
            node.context[self.key]['send_eth'] = list(set(node.context[self.key]['send_eth'] + [node]))


        # All the state variables written  node里面所有的被写的全局变量
        state_vars_written = node.state_variables_written
        '''
            def state_variables_written(self):
                """
                    list(StateVariable): State variables written
                """
                return list(self._state_vars_written)

        '''
        # Add the state variables written in internal calls  节点里面的内部调用也有可能对全局变量进行了写操作。内部调用与外部调用都是针对合约来说的
        '''
            @property
            def internal_calls(self):
                """
                    list(Function or SolidityFunction): List of internal/soldiity function calls
                """
                return list(self._internal_calls)
        '''
        for internal_call in node.internal_calls:
            # Filter to Function, as internal_call can be a solidity call  不考虑solidity call类型的内部调用只考虑函数类型的内部调用
            if isinstance(internal_call, Function):
                state_vars_written += internal_call.all_state_variables_written()
        '''
        到这里，state_vars_written就很完整了。包括了的节点里的被写的全局变量，还包括节点内部函数调用里的被写的全局变量
        '''

        read_then_written = [(v, node) for v in state_vars_written if v in node.context[self.key]['read']]  #可以看出node.cotext["reentrancy"]['read']里边存的是变量对象

        node.context[self.key]['read'] = list(set(node.context[self.key]['read'] + node.state_variables_read))
        # If a state variables was read and is then written, there is a dangerous call and ether were sent
        # We found a potential re-entrancy bug
        if (read_then_written and
                node.context[self.key]['calls'] and
                node.context[self.key]['send_eth']):
            # calls are ordered
            finding_key = (node.function,
                           tuple(set(node.context[self.key]['calls'])),
                           tuple(set(node.context[self.key]['send_eth'])))
            finding_vars = read_then_written
            if finding_key not in self.result:
                self.result[finding_key] = []
            self.result[finding_key] = list(set(self.result[finding_key] + finding_vars))

        sons = node.sons
        if contains_call and self._check_on_call_returned(node):  #本文件58行
            sons = sons[1:]

        for son in sons:
            self._explore(son, visited)

    def detect_reentrancy(self, contract):#self:就是Reentrancy类的一个实例对象，contract就是Contact实例对象
        """
        """
        for function in contract.functions:#从contract这个实例对象遍历出他的每一个函数Function实例对象记为function
            if function.is_implemented: #如果这个funtion对象是有实现的也就是这个函数有{}
                self._explore(function.entry_point, [])#我们得到这个function的入口点node。function.entry_point是在第三阶段，解析函数内容的时候封装进去的

    def detect(self):
        """
        """
        self.result = {}

        # if a node was already visited by another path  因为函数调用很随便啦
        # we will only explore it if the traversal brings new variables written
        # This speedup the exploration through a light fixpoint
        # Its particular useful on 'complex' functions with several loops and conditions
        self.visited_all_paths = {}   #self是指Reentrancy的实例

        for c in self.contracts:    #遍历所有的self.contracts列表取出每一个Contract对象
            self.detect_reentrancy(c)  #这个方法就在本文件156行左右

        results = []

        result_sorted = sorted(list(self.result.items()), key=lambda x:x[0][0].name)
        for (func, calls, send_eth), varsWritten in result_sorted:
            calls = list(set(calls))
            send_eth = list(set(send_eth))
#            if calls == send_eth:
#                calls_info = 'Call: {},'.format(calls_str)
#            else:
#                calls_info = 'Call: {}, Ether sent: {},'.format(calls_str, send_eth_str)
            info = '\tReentrancy in {}.{} ({}):\n'
            info = info.format(func.contract.name, func.name, func.source_mapping_str)
            info += '\t\tExternal calls:\n'
            for call_info in calls:
                info += '\t\t- {} ({})\n'.format(call_info.expression, call_info.source_mapping_str)
            if calls != send_eth:
                info += '\t\tExternal calls sending eth:\n'
                for call_info in send_eth:
                    info += '\t\t- {} ({})\n'.format(call_info.expression, call_info.source_mapping_str)
            info += '\t\tState variables written after the call(s):\n'
            for (v, node) in varsWritten:
                info +=  '\t\t- {} ({})\n'.format(v, node.source_mapping_str)
            self.log(info)

            sending_eth_json = []
            if calls != send_eth:
                sending_eth_json = [{'type' : 'external_calls_sending_eth',
                                     'expression': str(call_info.expression),
                                     'source_mapping': call_info.source_mapping}
                                    for call_info in calls]

            json = self.generate_json_result(info)
            self.add_function_to_json(func, json)
            json['elements'] += [{'type': 'external_calls',
                                  'expression': str(call_info.expression),
                                  'source_mapping': call_info.source_mapping}
                                 for call_info in calls]
            json['elements'] += sending_eth_json
            json['elements'] += [{'type':'variables_written',
                                   'name': v.name,
                                   'expression': str(node.expression),
                                   'source_mapping': node.source_mapping}
                                  for (v, node) in varsWritten]
            results.append(json)

        return results
