import logging
from slither.solc_parsing.expressions.expression_parsing import parse_expression

from slither.core.variables.variable import Variable

from slither.solc_parsing.solidity_types.type_parsing import parse_type, UnknownType

from slither.core.solidity_types.elementary_type import ElementaryType, NonElementaryType

logger = logging.getLogger("VariableDeclarationSolcParsing")

class MultipleVariablesDeclaration(Exception):
    '''
    This is raised on
    var (a,b) = ...
    It should occur only on local variable definition
    '''
    pass

class VariableDeclarationSolc(Variable):

    def __init__(self, var):   #var就是变量声明ast字典节点
        '''
            A variable can be declared through a statement, or directly.
            If it is through a statement, the following children may contain
            the init value.
            It may be possible that the variable is declared through a statement,
            but the init value is declared at the VariableDeclaration children level
        '''

        super(VariableDeclarationSolc, self).__init__()
        self._was_analyzed = False
        self._elem_to_parse = None
        self._initializedNotParsed = None

        self._is_compact_ast = False

        if 'nodeType' in var:
            self._is_compact_ast = True
            nodeType = var['nodeType']
            if nodeType in ['VariableDeclarationStatement', 'VariableDefinitionStatement']:
                if len(var['declarations'])>1:
                    raise MultipleVariablesDeclaration
                init = None
                if 'initialValue' in var:
                    init = var['initialValue']
                self._init_from_declaration(var['declarations'][0], init)
            elif  nodeType == 'VariableDeclaration':
                self._init_from_declaration(var, var['value'])
            else:
                logger.error('Incorrect variable declaration type {}'.format(nodeType))
                exit(-1)

        else:
            nodeType = var['name']

            if nodeType in ['VariableDeclarationStatement', 'VariableDefinitionStatement']:
                if len(var['children']) == 2:
                    init = var['children'][1]
                elif len(var['children']) == 1:
                    init = None
                elif len(var['children']) > 2:
                    raise MultipleVariablesDeclaration
                else:
                    logger.error('Variable declaration without children?'+var)
                    exit(-1)
                declaration = var['children'][0]
                self._init_from_declaration(declaration, init)
            elif  nodeType == 'VariableDeclaration':
                self._init_from_declaration(var, None)  #None的形参是init,给变量对象注入值进去，在本文件89行
            else:
                logger.error('Incorrect variable declaration type {}'.format(nodeType))
                exit(-1)

    @property
    def initialized(self):
        return self._initialized

    @property
    def uninitialized(self):
        return not self._initialized

    def _analyze_variable_attributes(self, attributes):
        if 'visibility' in attributes:
            self._visibility = attributes['visibility']
        else:
            self._visibility = 'internal'

    def _init_from_declaration(self, var, init):
        if self._is_compact_ast:
            attributes = var
            self._typeName = attributes['typeDescriptions']['typeString']
        else:
            assert len(var['children']) <= 2
            assert var['name'] == 'VariableDeclaration'

            attributes = var['attributes']
            self._typeName = attributes['type']

        self._name = attributes['name']   #从ast中得到变量的名字，注入到self(变量对象)._name中
        self._arrayDepth = 0
        self._isMapping = False
        self._mappingFrom = None
        self._mappingTo = False
        self._initial_expression = None
        self._type = None

        if 'constant' in attributes:
            self._is_constant = attributes['constant']  #attributres:{....,constant:false:true,....}

        self._analyze_variable_attributes(attributes)  #本文件83行 主要做了一个这个self._visibility = attributes['visibility'] 如“internal”

        if self._is_compact_ast:
            if var['typeName']:
                self._elem_to_parse = var['typeName']
            else:
                self._elem_to_parse = UnknownType(var['typeDescriptions']['typeString'])
        else:
            if not var['children']:
                # It happens on variable declared inside loop declaration
                try:
                    self._type = ElementaryType(self._typeName)
                    self._elem_to_parse = None
                except NonElementaryType:
                    self._elem_to_parse = UnknownType(self._typeName)
            else:
                self._elem_to_parse = var['children'][0]

        if self._is_compact_ast:
            self._initializedNotParsed = init
            if init:
                self._initialized = True
        else:
            if init: # there are two way to init a var local in the AST
                #print('11111111')  slither SimpleDAO.sol没有进来
                assert len(var['children']) <= 1
                self._initialized = True
                self._initializedNotParsed = init
            elif len(var['children']) in [0, 1]:
                self._initialized = False  #如果说这个变量声明节点的孩子是一个或2个，则这个变量是没有初始化的
                self._initializedNotParsed = []
            else:
                assert len(var['children']) == 2
                #print('111111111111') slither SimpleDAO.sol没有进来
                self._initialized = True
                self._initializedNotParsed = var['children'][1]    #如果有这个ast节点的话，因该是一个expression

    def analyze(self, caller_context): #对于此函数用于分析本地变量时来说，caller_context被传进来的是function对象
        # Can be re-analyzed due to inheritance
        if self._was_analyzed:#这个变量是否被分析过，被分析过直接返回
            return
        self._was_analyzed = True#将变量的_was_analyzed这个这个属性设置为True
        #print(self._elem_to_parse)看到{'attributes': {'name': 'uint', 'type': 'uint256'}, 'id': 31, 'name': 'ElementaryTypeName', 'src': '277:4:0'}
        #print(caller_context)看到withdraw
        if self._elem_to_parse: #elem是element缩写  self._elem_to_parse = var['children'][0]
            self._type = parse_type(self._elem_to_parse, caller_context)#这个函数功能是为了得到变量的类型，#对于此函数用于分析本地变量时来说，caller_context被传进来的是function对象
            self._elem_to_parse = None
        #print(self._initialized)
        #print(self._initializedNotParsed, caller_context)，对于slither SimpleDAO.sol来说self._initializedNotParsed=[]空
        #print(self._initialized)
        if self._initialized:   #T OR F 对于slither SimpleDAO.sol全为false
            #print("111111111")     SimpleDAO.sol就没有进来
            self._initial_expression = parse_expression(self._initializedNotParsed, caller_context)#self.__initializedNotParsed看本文件第146行，对于此函数用于分析本地变量时来说，caller_context被传进来的是function对象
            self._initializedNotParsed = None
