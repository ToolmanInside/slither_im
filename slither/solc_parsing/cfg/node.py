from slither.core.cfg.node import Node
from slither.core.cfg.node import NodeType
from slither.solc_parsing.expressions.expression_parsing import parse_expression
from slither.visitors.expression.read_var import ReadVar
from slither.visitors.expression.write_var import WriteVar
from slither.visitors.expression.find_calls import FindCalls

from slither.visitors.expression.export_values import ExportValues
from slither.core.declarations.solidity_variables import SolidityVariable, SolidityFunction
from slither.core.declarations.function import Function

from slither.core.variables.state_variable import StateVariable

from slither.core.expressions.identifier import Identifier
from slither.core.expressions.assignment_operation import AssignmentOperation, AssignmentOperationType

class NodeSolc(Node):

    def __init__(self, nodeType, nodeId):#nodeType就是例如NodeType.ENTRYPOINT=0X0
        super(NodeSolc, self).__init__(nodeType, nodeId)
        self._unparsed_expression = None

    def add_unparsed_expression(self, expression):
        assert self._unparsed_expression is None
        self._unparsed_expression = expression

    def analyze_expressions(self, caller_context):#如果caller_context=一个函数对象，说明局部
        if self.type == NodeType.VARIABLE and not self._expression: #self._expression对应的是ast中的某个表达式节点，eg:children[0]是条件
            self._expression = self.variable_declaration.expression
        if self._unparsed_expression:  #ast的字典
            expression = parse_expression(self._unparsed_expression, caller_context)  #self._unparsed_expression={name:"BinaryOperation"}
            #print(str(type(expression)))
            '''
                <class 'slither.core.expressions.assignment_operation.AssignmentOperation'>     credit[to] += msg.value;
                <class 'slither.core.expressions.index_access.IndexAccess'>                     credit[to];
                <class 'slither.core.expressions.binary_operation.BinaryOperation'>             credit[msg.sender]>= amount
                <class 'slither.core.expressions.call_expression.CallExpression'>               require(msg.sender.call.value(amount)());
                <class 'slither.core.expressions.assignment_operation.AssignmentOperation'>     credit[msg.sender]-=amount;
            '''
            self._expression = expression
            self._unparsed_expression = None
        #print(self.expression)输出如下
        '''
            None
            credit[to] += msg.value
            None
            credit[to]
            None
            credit[msg.sender] >= amount
            require(bool)(msg.sender.call.value(amount)())
            credit[msg.sender] -= amount
            None
        '''
        if self.expression:#如果一个节点的express属性不是空
            '''
                    def expression(self):
                        """
                            Expression: Expression of the node
                        """
                        return self._expression
            '''

            if self.type == NodeType.VARIABLE:#如果说这个节点的类型是变量类型  name in ['VariableDefinitionStatement', 'VariableDeclarationStatement']:
                # Update the expression to be an assignement to the variable
                #print(self.variable_declaration)
                self._expression = AssignmentOperation(Identifier(self.variable_declaration),#  new_node.add_variable_declaration(local_var)     left_expression  如果说这个节点的类型是变量类型,这个节点的self._expression被赋值一个赋值表达式
                                                       self.expression,   #right_expression
                                                       AssignmentOperationType.ASSIGN,#  "="
                                                       self.variable_declaration.type) #形参expression_return_type
            #print(self.expression)输出如下对于slither SimpleDAO.sol
            '''
                credit[to] += msg.value
                credit[to]
                credit[msg.sender] >= amount
                require(bool)(msg.sender.call.value(amount)())
                credit[msg.sender] -= amount    
            '''
            expression = self.expression
            pp = ReadVar(expression)
            #print(self._expression_vars_read)
            self._expression_vars_read = pp.result() #对于slither SimpDAO.sol是五个[]空

#            self._vars_read = [item for sublist in vars_read for item in sublist]
#            self._state_vars_read = [x for x in self.variables_read if\
#                                     isinstance(x, (StateVariable))]
#            self._solidity_vars_read = [x for x in self.variables_read if\
#                                        isinstance(x, (SolidityVariable))]

            pp = WriteVar(expression)
            self._expression_vars_written = pp.result()
            #print(self._expression_vars_written)
            '''
            []
            [<slither.core.expressions.identifier.Identifier object at 0x000001DC2C748748>]
            '''
            #print(self._expression_vars_written)输出如下对于slither SimpDAO.sol
            '''
                [<slither.core.expressions.identifier.Identifier object at 0x000001CAD2B67048>]   credit[to] += msg.value
                []
                []
                []
                [<slither.core.expressions.identifier.Identifier object at 0x000001CAD2B994E0>]   credit[msg.sender] -= amount  
            '''

#            self._vars_written = [item for sublist in vars_written for item in sublist]
#            self._state_vars_written = [x for x in self.variables_written if\
#                                        isinstance(x, StateVariable)]

            pp = FindCalls(expression)
            self._expression_calls = pp.result()
            #print(self._expression_calls)对于slither SimpleDAO.sol输出如下
            '''
                []
                []
                []
                [<slither.core.expressions.call_expression.CallExpression object at 0x000002C24E9E9208>, <slither.core.expressions.call_expression.CallExpression object at 0x000002C24E9E9438>, <slither.core.expressions.call_expression.CallExpression object at 0x000002C24E9E92E8>]
                []
            '''
            #print(str(self._expression_calls))输出同上
            '''
                @property
                def calls_as_expression(self):
                    return list(self._expression_calls)
            '''
            #for c in self.calls_as_expression:
                #print(c.called)对于slither SimpleDAO.sol输出如下
            '''
                require(bool)
                msg.sender.call.value(amount)
                msg.sender.call.value
            '''
            #for c in self.calls_as_expression:
                #print(str(type(c.called)))对于slither SimpleDAO.sol输出如下
            '''
                <class 'slither.core.expressions.identifier.Identifier'>      require(bool)
                <class 'slither.core.expressions.call_expression.CallExpression'>   msg.sender.call.value(amount)
                <class 'slither.core.expressions.member_access.MemberAccess'>   msg.sender.call.value
            '''
            self._external_calls_as_expressions = [c for c in self.calls_as_expression if not isinstance(c.called, Identifier)]
            #print(str(type(self._external_calls_as_expressions)))
            '''
                <class 'list'>
                <class 'list'>
                <class 'list'>
                <class 'list'>
                <class 'list'>
            '''
            #print(self._external_calls_as_expressions)
            '''
            
            []
            []
            []
            [<slither.core.expressions.call_expression.CallExpression object at 0x00000202FF2A9438>, <slither.core.expressions.call_expression.CallExpression object at 0x00000202FF2A92E8>]
            []
            '''


