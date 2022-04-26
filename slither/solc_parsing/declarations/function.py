"""
    Event module
"""
import logging
from slither.core.declarations.function import Function
from slither.core.cfg.node import NodeType
from slither.solc_parsing.cfg.node import NodeSolc
from slither.core.cfg.node import NodeType
from slither.core.cfg.node import link_nodes

from slither.solc_parsing.variables.local_variable import LocalVariableSolc
from slither.solc_parsing.variables.local_variable_init_from_tuple import LocalVariableInitFromTupleSolc
from slither.solc_parsing.variables.variable_declaration import MultipleVariablesDeclaration

from slither.solc_parsing.expressions.expression_parsing import parse_expression

from slither.core.expressions import AssignmentOperation
from slither.visitors.expression.export_values import ExportValues
from slither.visitors.expression.has_conditional import HasConditional

from slither.utils.expression_manipulations import SplitTernaryExpression

from slither.slithir.utils.variable_number import transform_slithir_vars_to_ssa

logger = logging.getLogger("FunctionSolc")

class FunctionSolc(Function):
    """
    Event class
    """
    # elems = [(type, name)]

    def __init__(self, function, contract):   #function是一个大字典这个字典里面是一个函数，contract就是ContractSolc04(Contract)的对象
        super(FunctionSolc, self).__init__()
        self._contract = contract
        if self.is_compact_ast:  #self.is_compact_ast下面的属性方法
            self._name = function['name']
        else:
            self._name = function['attributes'][self.get_key()]  #self._name=withdraw
        self._functionNotParsed = function  #function是一个大字典这个字典里面是一个函数
        self._params_was_analyzed = False
        self._content_was_analyzed = False
        self._counter_nodes = 0

    def get_key(self):
        return self.slither.get_key()  #self.slither在爸爸Function中属性函数

    def get_children(self, key):
        if self.is_compact_ast:
            return key
        return 'children'

    @property
    def is_compact_ast(self):
        return self.slither.is_compact_ast   #self.slither是父类Function的属性方法

    def _analyze_attributes(self):
        if self.is_compact_ast:
            attributes = self._functionNotParsed
        else:
            attributes = self._functionNotParsed['attributes']   #这个self._functionNotParse其实就是function的ast字典，因此同样attributes也就是大字典

        if 'payable' in attributes:    #一个name:"FunctionDefinition"ast节点,此节点会有attributes:{stateMutability:"payable|pure|view",constant:false|true,isConstructor:false|true,.....}
            self._payable = attributes['payable']
        if 'stateMutability' in attributes:
            if attributes['stateMutability'] == 'payable':
                self._payable = True
            elif attributes['stateMutability'] == 'pure':
                self._pure = True
                self._view = True
            elif attributes['stateMutability'] == 'view':
                self._view = True

        if 'constant' in attributes:
            self._view = attributes['constant']

        self._is_constructor = False

        if 'isConstructor' in attributes:
            self._is_constructor = attributes['isConstructor']

        if 'kind' in attributes:
            if attributes['kind'] == 'constructor':
                self._is_constructor = True

        if 'visibility' in attributes:
            self._visibility = attributes['visibility']
        # old solc
        elif 'public' in attributes:
            if attributes['public']:
                self._visibility = 'public'
            else:
                self._visibility = 'private'
        else:
            self._visibility = 'public'

        if 'payable' in attributes:
            self._payable = attributes['payable']

    def _new_node(self, node_type, src):#node_type就是NodeType类的常量例如NodeType.ENTRYPOINT=0X0，src:就像这cfg['src']，比如就像函数ast的第三个孩子就是name:"Block" src：xx:xxx:xx
        node = NodeSolc(node_type, self._counter_nodes)#其实就是用NodeSolc这个类来生成node对象实例，self._counter_nodes是函数实例的一个属性，就在本文件第43行被初始化为0，形参是nodeId
        node.set_offset(src, self.slither)#这个功能就是src:xxx:xxx:xx与源代码的行数相对应
        self._counter_nodes += 1 #._counter_nodes=0代表这个节点是NodeType.ENTRYPOINT
        node.set_function(self)#self._function=function
        self._nodes.append(node)#一个函数可以有很多节点被append到self._nodes列表。
        return node

    def _parse_if(self, ifStatement, node):#ifstatement={name:"IfStatement",id:xxx,src:xxx,children:[],attributes:xxx}，node
        # IfStatement = 'if' '(' Expression ')' Statement ( 'else' Statement )?
        falseStatement = None

        if self.is_compact_ast:
            condition = ifStatement['condition']
            # Note: check if the expression could be directly
            # parsed here
            condition_node = self._new_node(NodeType.IF, ifStatement['src'])
            condition_node.add_unparsed_expression(condition)
            link_nodes(node, condition_node)
            trueStatement = self._parse_statement(ifStatement['trueBody'], condition_node)
            if ifStatement['falseBody']:
                falseStatement = self._parse_statement(ifStatement['falseBody'], condition_node)
        else:
            children = ifStatement[self.get_children('children')]#对于slither.SimpleDAO.sol来说children有两个children[0]是条件，children[1]是name:block
            condition = children[0]
            # Note: check if the expression could be directly
            # parsed here
            #node=self._new_node(Node.ENTRYPOINT,cfg['src'])   cfg就是name:Block的那个ast节点字典
            condition_node = self._new_node(NodeType.IF, ifStatement['src'])#因为此时已经到了ifStatement['src']这一步，我们就应该创建一个新的节点，这个节点的类型是NodeType.IF
            condition_node.add_unparsed_expression(condition) #上边condition = children[0]。condition形参是express
            '''
                 def add_unparsed_expression(self, expression):
                    assert self._unparsed_expression is None
                    self._unparsed_expression = expression
            '''
            link_nodes(node, condition_node)#这个node就是NodeType.ENTRYPOINT， condition_node就是NodeType.IF； 这个函数在node.py文件中，node是爸爸,condition_node是儿子
            trueStatement = self._parse_statement(children[1], condition_node)#children[1]是name:block对应于ast就是if语句的block
            if len(children) == 3:
                falseStatement = self._parse_statement(children[2], condition_node)

        endIf_node = self._new_node(NodeType.ENDIF, ifStatement['src'])
        link_nodes(trueStatement, endIf_node)

        if falseStatement:
            link_nodes(falseStatement, endIf_node)
        else:
            link_nodes(condition_node, endIf_node)
        return endIf_node

    def _parse_while(self, whileStatement, node):
        # WhileStatement = 'while' '(' Expression ')' Statement

        node_startWhile = self._new_node(NodeType.STARTLOOP, whileStatement['src'])
        node_condition = self._new_node(NodeType.IFLOOP, whileStatement['src'])

        if self.is_compact_ast:
            node_condition.add_unparsed_expression(whileStatement['condition'])
            statement = self._parse_statement(whileStatement['body'], node_condition)
        else:
            children = whileStatement[self.get_children('children')]
            expression = children[0]
            node_condition.add_unparsed_expression(expression)
            statement = self._parse_statement(children[1], node_condition)

        node_endWhile = self._new_node(NodeType.ENDLOOP, whileStatement['src'])

        link_nodes(node, node_startWhile)
        link_nodes(node_startWhile, node_condition)
        link_nodes(statement, node_condition)
        link_nodes(node_condition, node_endWhile)

        return node_endWhile

    def _parse_for_compact_ast(self, statement, node):
        body = statement['body']
        init_expression = statement['initializationExpression']
        condition = statement['condition']
        loop_expression = statement['loopExpression']

        node_startLoop = self._new_node(NodeType.STARTLOOP, statement['src'])
        node_endLoop = self._new_node(NodeType.ENDLOOP, statement['src'])

        if init_expression:
            node_init_expression = self._parse_statement(init_expression, node)
            link_nodes(node_init_expression, node_startLoop)
        else:
            link_nodes(node, node_startLoop)

        if condition:
            node_condition = self._new_node(NodeType.IFLOOP, statement['src'])
            node_condition.add_unparsed_expression(condition)
            link_nodes(node_startLoop, node_condition)
            link_nodes(node_condition, node_endLoop)
        else:
            node_condition = node_startLoop

        node_body = self._parse_statement(body, node_condition)

        if loop_expression:
            node_LoopExpression = self._parse_statement(loop_expression, node_body)
            link_nodes(node_LoopExpression, node_startLoop)
        else:
            link_nodes(node_body, node_startLoop)

        if not condition:
            if not loop_expression:
                # TODO: fix case where loop has no expression
                link_nodes(node_startLoop, node_endLoop)
            else:
                link_nodes(node_LoopExpression, node_endLoop)

        return node_endLoop


    def _parse_for(self, statement, node):
        # ForStatement = 'for' '(' (SimpleStatement)? ';' (Expression)? ';' (ExpressionStatement)? ')' Statement

        # the handling of loop in the legacy ast is too complex
        # to integrate the comapct ast
        # its cleaner to do it separately
        if self.is_compact_ast:
            return self._parse_for_compact_ast(statement, node)

        hasInitExession = True
        hasCondition = True
        hasLoopExpression = True

        # Old solc version do not prevent in the attributes
        # if the loop has a init value /condition or expression
        # There is no way to determine that for(a;;) and for(;a;) are different with old solc
        if 'attributes' in statement:
            if 'initializationExpression' in statement:
                if not statement['initializationExpression']:
                    hasInitExession = False
            if 'condition' in statement:
                if not statement['condition']:
                    hasCondition = False
            if 'loopExpression' in statement:
                if not statement['loopExpression']:
                    hasLoopExpression = False


        node_startLoop = self._new_node(NodeType.STARTLOOP, statement['src'])
        node_endLoop = self._new_node(NodeType.ENDLOOP, statement['src'])

        children = statement[self.get_children('children')]

        if hasInitExession:
            if len(children) >= 2:
                if children[0][self.get_key()] in ['VariableDefinitionStatement',
                                           'VariableDeclarationStatement',
                                           'ExpressionStatement']:
                    node_initExpression = self._parse_statement(children[0], node)
                    link_nodes(node_initExpression, node_startLoop)
                else:
                    hasInitExession = False
            else:
                hasInitExession = False

        if not hasInitExession:
            link_nodes(node, node_startLoop)
        node_condition = node_startLoop

        if hasCondition:
            if hasInitExession and len(children) >= 2:
                candidate = children[1]
            else:
                candidate = children[0]
            if candidate[self.get_key()] not in ['VariableDefinitionStatement',
                                         'VariableDeclarationStatement',
                                         'ExpressionStatement']:
                node_condition = self._new_node(NodeType.IFLOOP, statement['src'])
                #expression = parse_expression(candidate, self)
                expression = candidate
                node_condition.add_unparsed_expression(expression)
                link_nodes(node_startLoop, node_condition)
                link_nodes(node_condition, node_endLoop)
                hasCondition = True
            else:
                hasCondition = False


        node_statement = self._parse_statement(children[-1], node_condition)

        node_LoopExpression = node_statement
        if hasLoopExpression:
            if len(children) > 2:
                if children[-2][self.get_key()] == 'ExpressionStatement':
                    node_LoopExpression = self._parse_statement(children[-2], node_statement)
            if not hasCondition:
                link_nodes(node_LoopExpression, node_endLoop)

        if not hasCondition and not hasLoopExpression:
            link_nodes(node, node_endLoop)

        link_nodes(node_LoopExpression, node_startLoop)

        return node_endLoop

    def _parse_dowhile(self, doWhilestatement, node):

        node_startDoWhile = self._new_node(NodeType.STARTLOOP, doWhilestatement['src'])
        node_condition = self._new_node(NodeType.IFLOOP, doWhilestatement['src'])

        if self.is_compact_ast:
            node_condition.add_unparsed_expression(doWhilestatement['condition'])
            statement = self._parse_statement(doWhilestatement['body'], node_condition)
        else:
            children = doWhilestatement[self.get_children('children')]
            # same order in the AST as while
            expression = children[0]
            node_condition.add_unparsed_expression(expression)
            statement = self._parse_statement(children[1], node_condition)

        node_endDoWhile = self._new_node(NodeType.ENDLOOP, doWhilestatement['src'])

        link_nodes(node, node_startDoWhile)
        link_nodes(node_startDoWhile, node_condition.sons[0])
        link_nodes(statement, node_condition)
        link_nodes(node_condition, node_endDoWhile)
        return node_endDoWhile

    def _parse_variable_definition(self, statement, node):
        try:
            local_var = LocalVariableSolc(statement)
            local_var.set_function(self)
            local_var.set_offset(statement['src'], self.contract.slither)

            self._variables[local_var.name] = local_var
            #local_var.analyze(self)

            new_node = self._new_node(NodeType.VARIABLE, statement['src'])
            new_node.add_variable_declaration(local_var)
            link_nodes(node, new_node)
            return new_node
        except MultipleVariablesDeclaration:
            # Custom handling of var (a,b) = .. style declaration
            if self.is_compact_ast:
                variables = statement['declarations']
                count = len(variables)

                if statement['initialValue']['nodeType'] == 'TupleExpression':
                    inits = statement['initialValue']['components']
                    i = 0
                    new_node = node
                    for variable in variables:
                        init = inits[i]
                        src = variable['src']
                        i = i+1

                        new_statement = {'nodeType':'VariableDefinitionStatement',
                                         'src': src,
                                         'declarations':[variable],
                                         'initialValue':init}
                        new_node = self._parse_variable_definition(new_statement, new_node)

                else:
                    # If we have
                    # var (a, b) = f()
                    # we can split in multiple declarations, without init
                    # Then we craft one expression that does the assignment                   
                    variables = []
                    i = 0
                    new_node = node
                    for variable in statement['declarations']:
                        i = i+1
                        if variable:
                            src = variable['src']
                            # Create a fake statement to be consistent
                            new_statement = {'nodeType':'VariableDefinitionStatement',
                                             'src': src,
                                             'declarations':[variable]}
                            variables.append(variable)

                            new_node = self._parse_variable_definition_init_tuple(new_statement,
                                                                                  i,
                                                                                  new_node)

                    var_identifiers = []
                    # craft of the expression doing the assignement
                    for v in variables:
                        identifier = {
                            'nodeType':'Identifier',
                            'src': v['src'],
                            'name': v['name'],
                            'typeDescriptions': {
                                'typeString':v['typeDescriptions']['typeString']
                            }
                        }
                        var_identifiers.append(identifier)

                    tuple_expression = {'nodeType':'TupleExpression',
                                        'src': statement['src'],
                                        'components':var_identifiers}

                    expression = {
                        'nodeType' : 'Assignment',
                        'src':statement['src'],
                        'operator': '=',
                        'type':'tuple()',
                        'leftHandSide': tuple_expression,
                        'rightHandSide': statement['initialValue'],
                        'typeDescriptions': {'typeString':'tuple()'}
                        }
                    node = new_node
                    new_node = self._new_node(NodeType.EXPRESSION, statement['src'])
                    new_node.add_unparsed_expression(expression)
                    link_nodes(node, new_node)


            else:
                count = 0
                children = statement[self.get_children('children')]
                child = children[0]
                while child[self.get_key()] == 'VariableDeclaration':
                    count = count +1
                    child = children[count]

                assert len(children) == (count + 1)
                tuple_vars = children[count]


                variables_declaration = children[0:count]
                i = 0
                new_node = node
                if tuple_vars[self.get_key()] == 'TupleExpression':
                    assert len(tuple_vars[self.get_children('children')]) == count
                    for variable in variables_declaration:
                        init = tuple_vars[self.get_children('children')][i]
                        src = variable['src']
                        i = i+1
                        # Create a fake statement to be consistent
                        new_statement = {self.get_key():'VariableDefinitionStatement',
                                         'src': src,
                                         self.get_children('children'):[variable, init]}

                        new_node = self._parse_variable_definition(new_statement, new_node)
                else:
                    # If we have
                    # var (a, b) = f()
                    # we can split in multiple declarations, without init
                    # Then we craft one expression that does the assignment
                    assert tuple_vars[self.get_key()] in ['FunctionCall', 'Conditional']
                    variables = []
                    for variable in variables_declaration:
                        src = variable['src']
                        i = i+1
                        # Create a fake statement to be consistent
                        new_statement = {self.get_key():'VariableDefinitionStatement',
                                         'src': src,
                                         self.get_children('children'):[variable]}
                        variables.append(variable)

                        new_node = self._parse_variable_definition_init_tuple(new_statement, i, new_node)
                    var_identifiers = []
                    # craft of the expression doing the assignement
                    for v in variables:
                        identifier = {
                            self.get_key() : 'Identifier',
                            'src': v['src'],
                            'attributes': {
                                    'value': v['attributes'][self.get_key()],
                                    'type': v['attributes']['type']}
                        }
                        var_identifiers.append(identifier)

                    expression = {
                        self.get_key() : 'Assignment',
                        'src':statement['src'],
                        'attributes': {'operator': '=',
                                       'type':'tuple()'},
                        self.get_children('children'):
                        [{self.get_key(): 'TupleExpression',
                          'src': statement['src'],
                          self.get_children('children'): var_identifiers},
                         tuple_vars]}
                    node = new_node
                    new_node = self._new_node(NodeType.EXPRESSION, statement['src'])
                    new_node.add_unparsed_expression(expression)
                    link_nodes(node, new_node)


            return new_node

    def _parse_variable_definition_init_tuple(self, statement, index, node):
        local_var = LocalVariableInitFromTupleSolc(statement, index)
        #local_var = LocalVariableSolc(statement[self.get_children('children')][0], statement[self.get_children('children')][1::])
        local_var.set_function(self)
        local_var.set_offset(statement['src'], self.contract.slither)

        self._variables[local_var.name] = local_var
#        local_var.analyze(self)

        new_node = self._new_node(NodeType.VARIABLE, statement['src'])
        new_node.add_variable_declaration(local_var)
        link_nodes(node, new_node)
        return new_node


    def _parse_statement(self, statement, node):
        """

        Return:
            node
        """
        # Statement = IfStatement | WhileStatement | ForStatement | Block | InlineAssemblyStatement |
        #            ( DoWhileStatement | PlaceholderStatement | Continue | Break | Return |
        #                          Throw | EmitStatement | SimpleStatement ) ';'
        # SimpleStatement = VariableDefinition | ExpressionStatement

        name = statement[self.get_key()]
        # SimpleStatement = VariableDefinition | ExpressionStatement
        if name == 'IfStatement':  #没错，对于slither SimpleDAO.sol来说只有这一个
            node = self._parse_if(statement, node)  #statement={name:"IfStatement",id:xxx,src:xxx,children:xxx,attributes:xxx}    return endIf_node
        elif name == 'WhileStatement':
            node = self._parse_while(statement, node)
        elif name == 'ForStatement':
            node = self._parse_for(statement, node)
        elif name == 'Block':
            node = self._parse_block(statement, node) #statement={name:"Block",id:xxx,src:xxx,children:xxx,attributes:xxx}比如说是if(){}的block
        elif name == 'InlineAssembly':
            break_node = self._new_node(NodeType.ASSEMBLY, statement['src'])
            self._contains_assembly = True
            link_nodes(node, break_node)
            node = break_node
        elif name == 'DoWhileStatement':
            node = self._parse_dowhile(statement, node)
        # For Continue / Break / Return / Throw
        # The is fixed later
        elif name == 'Continue':
            continue_node = self._new_node(NodeType.CONTINUE, statement['src'])
            link_nodes(node, continue_node)
            node = continue_node
        elif name == 'Break':
            break_node = self._new_node(NodeType.BREAK, statement['src'])
            link_nodes(node, break_node)
            node = break_node
        elif name == 'Return':
            return_node = self._new_node(NodeType.RETURN, statement['src'])
            link_nodes(node, return_node)
            if self.is_compact_ast:
                if statement['expression']:
                    return_node.add_unparsed_expression(statement['expression'])
            else:
                if self.get_children('children') in statement and statement[self.get_children('children')]:
                    assert len(statement[self.get_children('children')]) == 1
                    expression = statement[self.get_children('children')][0]  #此时这个expression={attributes:{},children:[],id:27,name:"IndexAccess",src:"241:10:0"}对应于原代码的return credit[to]
                    return_node.add_unparsed_expression(expression)   #因为这个expression 还是简单的字典所以这个节点对象把他添加到未解析的表达式
                    '''
                        def add_unparsed_expression(self, expression):
                            assert self._unparsed_expression is None
                            self._unparsed_expression = expression
                    '''
            node = return_node
        elif name == 'Throw':
            throw_node = self._new_node(NodeType.THROW, statement['src'])
            link_nodes(node, throw_node)
            node = throw_node
        elif name == 'EmitStatement':
            #expression = parse_expression(statement[self.get_children('children')][0], self)
            if self.is_compact_ast:
                expression = statement['eventCall']
            else:
                expression = statement[self.get_children('children')][0]
            new_node = self._new_node(NodeType.EXPRESSION, statement['src'])
            new_node.add_unparsed_expression(expression)
            link_nodes(node, new_node)
            node = new_node
        elif name in ['VariableDefinitionStatement', 'VariableDeclarationStatement']:
            node = self._parse_variable_definition(statement, node)   #本文件322行  new_node = self._new_node(NodeType.VARIABLE, statement['src'])
            '''
                new_node = self._new_node(NodeType.VARIABLE, statement['src'])
                new_node.add_variable_declaration(local_var)
                link_nodes(node, new_node)
                return new_node
            '''
        elif name == 'ExpressionStatement':
            #assert len(statement[self.get_children('expression')]) == 1
            #assert not 'attributes' in statement
            #expression = parse_expression(statement[self.get_children('children')][0], self)
            if self.is_compact_ast:
                expression = statement[self.get_children('expression')]
            else:
                expression = statement[self.get_children('expression')][0] #express={name:FunctionCall}对应于SimpleDAO.sol中require(msg.sender.call.value(amount)());   注意因为不是紧凑的AST所以self.get_children('expression')='children'，expression就对应与if的block中第一条表达式语句的头一个孩子
            new_node = self._new_node(NodeType.EXPRESSION, statement['src'])#因为此时我们已经到达if语句块的第一条表达式语句了，所以我们应该生成一个new_node。statement={name:ExpressionStatement}
            new_node.add_unparsed_expression(expression)
            '''
                condition_node.add_unparsed_expression(condition) #上边condition = children[0]。condition形参是express
            
                 def add_unparsed_expression(self, expression):
                    assert self._unparsed_expression is None
                    self._unparsed_expression = expression
            
            '''
            link_nodes(node, new_node)#node此时是condition_node是爸爸，new_node是儿子,,, new_node = self._new_node(NodeType.EXPRESSION, statement['src'])
            node = new_node
        else:
            logger.error('Statement not parsed %s'%name)
            exit(-1)

        return node

    def _parse_block(self, block, node):#这个block就是函数block字典，函数的block对应于一个node
        '''
        Return:
            Node
        '''
        assert block[self.get_key()] == 'Block'

        if self.is_compact_ast:
            statements = block['statements']
        else:
            statements = block[self.get_children('children')]  #得到的这个statements其实就是对应ast函数Block的孩子比如Ifstatement，whileStatement什么的。对于slither SimpleDAO.sol来说就是只有name:'IfStatement'这一个孩子

        for statement in statements:
            node = self._parse_statement(statement, node)#开始分析name:'IfStatement'这块,这个函数本文件在493行
        return node

    def _parse_cfg(self, cfg):#这个cfg就是函数block字典

        assert cfg[self.get_key()] == 'Block'

        node = self._new_node(NodeType.ENTRYPOINT, cfg['src'])#这个函数在本文件100行左右，用于生成一个新的node对象，通过一个节点的类型和一个函数体（块）两个參數生成的node对象,NodeType.ENTRYPOINT=0X0，NodeType类型的一个常量
        self._entry_point = node#因为entry_point节点比较关键所以有一个funtion的属性self._entry_point来指向它

        if self.is_compact_ast:
            statements = cfg['statements']
        else:
            statements = cfg[self.get_children('children')]#函数的ast有三个孩子嘛，第一个孩子是函数參數，第二个孩子是返回參數，第三个孩子name:'Block'也就是这个cfg。所以statements是第三个孩子的孩子

        if not statements:#因为有的函数确实有Block但Block里边神马都没有写那么我们函数对象就有一个属性self._is_empty=True
            self._is_empty = True
        else:
            self._is_empty = False #函数确实有Block,并且Block里边确实有孩子也就是并不是一个空的大括号，此时我们就要去分析里面的东西了
            self._parse_block(cfg, node)  #这个函数在本文件577行这个函数返回node。，这个cfg就对应于AST中name：FuntionDefinition的它的第三个孩子也就是name:'Block'所在的ast节点，node就是函数体的入口点
            self._remove_incorrect_edges()#比如说Node.BREAK节点后边的节点得处理，比如Node.CONTINUE,Node.THROW,Node.RETURN。
            self._remove_alone_endif()#这个很简单，点进去就能看懂

    def _find_end_loop(self, node, visited):#这个node就是那个node.type=NodeType.BREAK
        if node in visited:
            return None

        if node.type == NodeType.ENDLOOP:
            return node

        visited = visited + [node]
        for son in node.sons:
            ret = self._find_end_loop(son, visited)
            if ret:
                return ret

        return None

    def _find_start_loop(self, node, visited):
        if node in visited:
            return None

        if node.type == NodeType.STARTLOOP:
            return node

        visited = visited + [node]
        for father in node.fathers:
            ret = self._find_start_loop(father, visited)
            if ret:
                return ret

        return None

    def _fix_break_node(self, node):#这个node就是那个node.type=NodeType.BREAK
        end_node = self._find_end_loop(node, [])#这个node就是那个node.type=NodeType.BREAK,去找循环末尾NodeType.ENDLOOP并将此节点返回回来记为end_node，这个node就是那个node.type=NodeType.BREAK

        if not end_node:  #如果就没有找到NodeType.ENDLOOP这个节点那么就说明这个NodeType.BREAK就不在循环体中
            logger.error('Break in no-loop context {}'.format(node))
            exit(-1)

        for son in node.sons:   #此时因为已经找到了循环的末尾节点，我就应该把BREAK节点的儿子全部断开，重新设置为end_node.表示跳出整个循环体
            son.remove_father(node)
        node.set_sons([end_node])
        end_node.add_father(node)

    def _fix_continue_node(self, node):#这个node就是那个node.type=NodeType.CONTINUE
        start_node = self._find_start_loop(node, [])#这个node就是那个node.type=NodeType.CONTINUE,去找循环末尾NodeType.STARTLOOP并将此节点返回回来记为start_node，这个node就是那个node.type=NodeType.BREAK

        if not start_node:#如果就没有找到NodeType.STARTLOOP这个节点那么就说明这个NodeType.CONTINUE就不在循环体中
            logger.error('Continue in no-loop context {}'.format(node.nodeId()))
            exit(-1)

        for son in node.sons:  #此时因为已经找到了循环的开始节点，我就应该把CONTINUE节点的儿子全部断开，重新设置为start_node.表示跳出本轮循环
            son.remove_father(node)
        node.set_sons([start_node])
        start_node.add_father(node)

    def _remove_incorrect_edges(self):
        for node in self._nodes: #遍历一个函数中的所有节点，基本上是从NodeType.ENTRYPOINT开始遍历的
            if node.type in [NodeType.RETURN, NodeType.THROW]:  #这个if为了完成return和throw语句之后的语句被切断父子关系
                for son in node.sons:
                    son.remove_father(node)
                node.set_sons([])
            if node.type in [NodeType.BREAK]:#如果遍历到BREAK节点，就要重构节点连接
                self._fix_break_node(node)
            if node.type in [NodeType.CONTINUE]:#如果遍历到CONTINUE节点，就要重构节点连接
                self._fix_continue_node(node)

    def _remove_alone_endif(self):
        """
            Can occur on:
            if(..){
                return
            }
            else{
                return
            }

            Iterate until a fix point to remove the ENDIF node
            creates on the following pattern
            if(){
                return
            }
            else if(){
                return
            }
        """
        prev_nodes = []
        while set(prev_nodes) != set(self.nodes):
            prev_nodes = self.nodes
            to_remove = []
            for node in self.nodes:
                if node.type == NodeType.ENDIF and not node.fathers:
                    for son in node.sons:
                        son.remove_father(node)
                    node.set_sons([])
                    to_remove.append(node)
            self._nodes = [n for n in self.nodes if not n in to_remove]
#
    def _parse_params(self, params):
        assert params[self.get_key()] == 'ParameterList'   #self.get_key()==name

        if self.is_compact_ast:
            params = params['parameters']
        else:
            params = params[self.get_children('children')]

        for param in params:
            assert param[self.get_key()] == 'VariableDeclaration'

            local_var = LocalVariableSolc(param)  #输入參數里边的变量声明就是本地变量对象，param是name：'VariableDeclaration'的ast字典节点

            local_var.set_function(self)#给本地变量 self._function属性赋值，在这里其实就是參數里面声明的变量
            local_var.set_offset(param['src'], self.contract.slither)  #找这个本地变量对应源文件的行数
            local_var.analyze(self)

            # see https://solidity.readthedocs.io/en/v0.4.24/types.html?highlight=storage%20location#data-location
            if local_var.location == 'default':
                local_var.set_location('memory')
                '''
                     def set_location(self, loc):
                        self._location = loc
                '''

            self._variables[local_var.name] = local_var   #self._variables={local_var.name:local_var}类比于self(合约对象)._functions={function.name:function_var}
            self._parameters.append(local_var)

    def _parse_returns(self, returns):

        assert returns[self.get_key()] == 'ParameterList'

        if self.is_compact_ast:
            returns = returns['parameters']
        else:
            returns = returns[self.get_children('children')]

        for ret in returns:
            assert ret[self.get_key()] == 'VariableDeclaration'

            local_var = LocalVariableSolc(ret)

            local_var.set_function(self)
            local_var.set_offset(ret['src'], self.contract.slither)
            local_var.analyze(self)

            # see https://solidity.readthedocs.io/en/v0.4.24/types.html?highlight=storage%20location#data-location
            if local_var.location == 'default':
                local_var.set_location('memory')

            self._variables[local_var.name] = local_var
            self._returns.append(local_var)


    def _parse_modifier(self, modifier):
        m = parse_expression(modifier, self)
        self._expression_modifiers.append(m)
        self._modifiers += [m for m in ExportValues(m).result() if isinstance(m, Function)]


    def analyze_params(self):
        # Can be re-analyzed due to inheritance
        if self._params_was_analyzed:    #如果这个參數被分析过（由于继承的原因）self（function）._params_was_analyzed==true
            return

        self._params_was_analyzed = True

        self._analyze_attributes()  #在本文件57行 ,我们就从function的ast的attributes进行分析,通过这个函数就可以把funtion实例对象的很多关于函数层面的属性就就给注入进去值了，比如self._visibility='public'

        if self.is_compact_ast:
            params = self._functionNotParsed['parameters']
            returns = self._functionNotParsed['returnParameters']
        else:
            children = self._functionNotParsed[self.get_children('children')]   # #这个self._functionNotParse其实就是function的ast字典,对于Slither SimpleDAO.sol这个self.get_children('children')='children'
            '''
                    def get_children(self, key):
                        if self.is_compact_ast:
                            return key
                        return 'children'
            '''
            params = children[0] #此时输入參數ast节点得到，同样也是大字典{name:"ParameterList"}
            returns = children[1]#此时返回參數ast节点得到，同样也是大字典{name:"ParameterList"}

        if params:  #ast大字典   大字典{name:"ParameterList"}
            self._parse_params(params)
        if returns:
            self._parse_returns(returns)

    def analyze_content(self):
        if self._content_was_analyzed:#如果说function对象_content_was_analyzed这个属性为true，jiu说明这个funtion对象已经被analyze过了直接return
            return

        self._content_was_analyzed = True

        if self.is_compact_ast:
            body = self._functionNotParsed['body']

            if body and body[self.get_key()] == 'Block':
                self._is_implemented = True
                self._parse_cfg(body)

            for modifier in self._functionNotParsed['modifiers']:
                self._parse_modifier(modifier)

        else:
            children = self._functionNotParsed[self.get_children('children')]#在本文件第40行self._functionNotParsed=function
            self._is_implemented = False
            for child in children[2:]:    #child是个字典
                if child[self.get_key()] == 'Block':
                    self._is_implemented = True#如果说这个这个函数对应的ast的child们中有一个child的名字是block就证明这个函数有函数体所以就设置这个函数的对象self._is_implemented=true
                    self._parse_cfg(child)#因为选出了函数对象中的'Block'的那个child,就来分析这个chlild也就是函数块的对象
    
            # Parse modifier after parsing all the block
            # In the case a local variable is used in the modifier
            for child in children[2:]:#对于slither SimpleDAO.sol来说因为没有modifier。所以这块没有执行
                if child[self.get_key()] == 'ModifierInvocation':
                    self._parse_modifier(child)
        #print(self.variables)
        #print(str(self.variables))
        #print(str(type(self.variables)))
        for local_vars in self.variables:#遍历出这个函数对象的所有本地变量。

            #print("111")
            local_vars.analyze(self) #对这些本地变量逐个进行分析

        for node in self.nodes:
            node.analyze_expressions(self)

        ternary_found = True#ternary 三元
        while ternary_found:
            ternary_found = False
            for node in self.nodes:
                has_cond = HasConditional(node.expression)
                if has_cond.result():
                    st = SplitTernaryExpression(node.expression)
                    condition = st.condition
                    assert condition
                    true_expr = st.true_expression
                    false_expr = st.false_expression
                    self.split_ternary_node(node, condition, true_expr, false_expr)
                    ternary_found = True
                    break
        self._remove_alone_endif()


    def convert_expression_to_slithir(self):
        for node in self.nodes:
            node.slithir_generation()
        transform_slithir_vars_to_ssa(self)
        self._analyze_read_write()
        self._analyze_calls()
 

    def split_ternary_node(self, node, condition, true_expr, false_expr):
        condition_node = self._new_node(NodeType.IF, node.source_mapping)
        condition_node.add_expression(condition)
        condition_node.analyze_expressions(self)

        if node.type == NodeType.VARIABLE:
            condition_node.add_variable_declaration(node.variable_declaration)

        true_node = self._new_node(NodeType.EXPRESSION, node.source_mapping)
        if node.type == NodeType.VARIABLE:
            assert isinstance(true_expr, AssignmentOperation)
            #true_expr = true_expr.expression_right
        true_node.add_expression(true_expr)
        true_node.analyze_expressions(self)

        false_node = self._new_node(NodeType.EXPRESSION, node.source_mapping)
        if node.type == NodeType.VARIABLE:
            assert isinstance(false_expr, AssignmentOperation)
            #false_expr = false_expr.expression_right
        false_node.add_expression(false_expr)
        false_node.analyze_expressions(self)

        endif_node = self._new_node(NodeType.ENDIF, node.source_mapping)

        for father in node.fathers:
            father.remove_son(node)
            father.add_son(condition_node)
            condition_node.add_father(father)

        for son in node.sons:
            son.remove_father(node)
            son.add_father(endif_node)
            endif_node.add_son(son)

        link_nodes(condition_node, true_node)
        link_nodes(condition_node, false_node)


        if not true_node.type in [NodeType.THROW, NodeType.RETURN]:
           link_nodes(true_node, endif_node)
        if not false_node.type in [NodeType.THROW, NodeType.RETURN]:
            link_nodes(false_node, endif_node)

        self._nodes = [n for n in self._nodes if n.node_id != node.node_id]


