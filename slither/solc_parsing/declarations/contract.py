import logging

from slither.core.declarations.contract import Contract
from slither.core.declarations.enum import Enum

from slither.solc_parsing.declarations.structure import StructureSolc
from slither.solc_parsing.declarations.event import EventSolc
from slither.solc_parsing.declarations.modifier import ModifierSolc
from slither.solc_parsing.declarations.function import FunctionSolc

from slither.solc_parsing.variables.state_variable import StateVariableSolc

from slither.solc_parsing.solidity_types.type_parsing import parse_type

logger = logging.getLogger("ContractSolcParsing")

class ContractSolc04(Contract):


    def __init__(self, slitherSolc, data):#data是一个这样的字典 {'attributes':xxxxxx, 'children':[xxx,xxxx,....], 'id':xxx, 'name':'ContractDefinition', 'src':xxx}
        assert slitherSolc.solc_version.startswith('0.4')
        super(ContractSolc04, self).__init__()# 调用父类Contract的__init__()

        self.set_slither(slitherSolc)  #在爷爷ChildSlither中
        self._data = data

        self._functionsNotParsed = []
        self._modifiersNotParsed = []
        self._functions_no_params = []
        self._modifiers_no_params = []
        self._eventsNotParsed = []
        self._variablesNotParsed = []
        self._enumsNotParsed = []
        self._structuresNotParsed = []
        self._usingForNotParsed = []

        self._is_analyzed = False

        # use to remap inheritance id
        self._remapping = {}

        # Export info
        if self.is_compact_ast:   #在本文件70多行  ,因为我们提供的不是compact_ast所以if不执行
            self._name = self._data['name']
        else:
            self._name = self._data['attributes'][self.get_key()] #self.get_key()='name'

        self._id = self._data['id']

        self._inheritance = []

        self._parse_contract_info()   #本文件79行
        self._parse_contract_items()


    @property
    def is_analyzed(self):
        return self._is_analyzed

    def get_key(self):
        return self.slither.get_key()

    def get_children(self, key='nodes'):
        if self.is_compact_ast:
            return key
        return 'children'

    @property
    def remapping(self):
        return self._remapping

    @property
    def is_compact_ast(self):
        return self.slither.is_compact_ast   #self.slither在爷爷ChildSlither中的一个属性方法。返回self._slither是一个SlitherSolc对象

    def set_is_analyzed(self, is_analyzed):
        self._is_analyzed = is_analyzed

    def _parse_contract_info(self):
        if self.is_compact_ast:
            attributes = self._data
        else:
            attributes = self._data['attributes']

        self.isInterface = False
        if 'contractKind' in attributes: #'contractKind'是attributes字典中的一个键
            if attributes['contractKind'] == 'interface':
                self.isInterface = True
            self._kind = attributes['contractKind']   #self._kind从爸爸里面继承的属性
        self.linearizedBaseContracts = attributes['linearizedBaseContracts']
        self.fullyImplemented = attributes['fullyImplemented']

        # trufle does some re-mapping of id
        if 'baseContracts' in self._data:
            for elem in self._data['baseContracts']:
                if elem['nodeType'] == 'InheritanceSpecifier':
                    self._remapping[elem['baseName']['referencedDeclaration']] = elem['baseName']['name']

    def _parse_contract_items(self):
        if not self.get_children() in self._data: # empty contract  self.get_children()返回的是一个'children', self._data=data其实就是data是一个这样的字典 {'attributes':xxxxxx, 'children':[xxx,xxxx,....], 'id':xxx, 'name':'ContractDefinition', 'src':xxx}
            return
        #print(self.get_key())
        #print('1111')
        for item in self._data[self.get_children()]:#每个item是字典
            if item[self.get_key()] == 'FunctionDefinition':  #self.get_key()返回的是'name'
                self._functionsNotParsed.append(item)   #self._functionNotParsed属性是在本文件声明的这样的列表[{},{},{}]
            elif item[self.get_key()] == 'EventDefinition':
                self._eventsNotParsed.append(item)
            elif item[self.get_key()] == 'InheritanceSpecifier':
                # we dont need to parse it as it is redundant
                # with self.linearizedBaseContracts
                continue
            elif item[self.get_key()] == 'VariableDeclaration':
                self._variablesNotParsed.append(item)
            elif item[self.get_key()] == 'EnumDefinition':
                self._enumsNotParsed.append(item)
            elif item[self.get_key()] == 'ModifierDefinition':
                self._modifiersNotParsed.append(item)
            elif item[self.get_key()] == 'StructDefinition':
                self._structuresNotParsed.append(item)
            elif item[self.get_key()] == 'UsingForDirective':
                self._usingForNotParsed.append(item)
            else:
                logger.error('Unknown contract item: '+item[self.get_key()])
                exit(-1)
        return

    def analyze_using_for(self):
        for father in self.inheritance:
            self._using_for.update(father.using_for)

        if self.is_compact_ast:
            for using_for in self._usingForNotParsed:
                lib_name = parse_type(using_for['libraryName'], self)
                if 'typeName' in using_for and using_for['typeName']:
                    type_name = parse_type(using_for['typeName'], self)
                else:
                    type_name = '*'
                if not type_name in self._using_for:
                    self.using_for[type_name] = []
                self._using_for[type_name].append(lib_name)
        else:
            for using_for in self._usingForNotParsed:
                #print('1111')
                children = using_for[self.get_children()]
                assert children and len(children) <= 2
                if len(children) == 2:
                    new = parse_type(children[0], self)
                    old = parse_type(children[1], self)
                else:
                    new = parse_type(children[0], self)
                    old = '*'
                if not old in self._using_for:
                    self.using_for[old] = []
                self._using_for[old].append(new)
        self._usingForNotParsed = []

    def analyze_enums(self):

        for father in self.inheritance:
            self._enums.update(father.enums_as_dict())
        #print(self._enumsNotParsed)
        for enum in self._enumsNotParsed:  #对于slither SimpleDAO.sol来说self._enumsNotParsed为空列表
            # for enum, we can parse and analyze it 
            # at the same time
            self._analyze_enum(enum)
        self._enumsNotParsed = None

    def _analyze_enum(self, enum):
        # Enum can be parsed in one pass
        if self.is_compact_ast:
            name = enum['name']
            canonicalName = enum['canonicalName']
        else:
            name = enum['attributes'][self.get_key()]
            if 'canonicalName' in enum['attributes']:
                canonicalName = enum['attributes']['canonicalName']
            else:
                canonicalName = self.name + '.' + name
        values = []
        for child in enum[self.get_children('members')]:
            assert child[self.get_key()] == 'EnumValue'
            if self.is_compact_ast:
                values.append(child['name'])
            else:
                values.append(child['attributes'][self.get_key()])

        new_enum = Enum(name, canonicalName, values)
        new_enum.set_contract(self)
        new_enum.set_offset(enum['src'], self.slither)
        self._enums[canonicalName] = new_enum

    def _parse_struct(self, struct):
        #print('111')
        if self.is_compact_ast:
            name = struct['name']
            attributes = struct
        else:
            name = struct['attributes'][self.get_key()]
            attributes = struct['attributes']
        if 'canonicalName' in attributes:
            canonicalName = attributes['canonicalName']
        else:
            canonicalName = self.name + '.' + name

        if self.get_children('members') in struct:
            children = struct[self.get_children('members')]
        else:
            children = [] # empty struct
        st = StructureSolc(name, canonicalName, children)
        st.set_contract(self)
        st.set_offset(struct['src'], self.slither)
        self._structures[name] = st

    def _analyze_struct(self, struct):
        struct.analyze()

    def parse_structs(self):
        for father in self.inheritance_reverse:
            self._structures.update(father.structures_as_dict())
        #print(self._structuresNotParsed)
        for struct in self._structuresNotParsed:
            self._parse_struct(struct)  #对于slither SimpleDAO.sol这块没运行
        self._structuresNotParsed = None

    def analyze_structs(self):
        for struct in self.structures:
            self._analyze_struct(struct)


    def analyze_events(self):
        for father in self.inheritance_reverse:
            self._events.update(father.events_as_dict())

        for event_to_parse in self._eventsNotParsed:
            event = EventSolc(event_to_parse, self)
            event.analyze(self)
            event.set_contract(self)
            event.set_offset(event_to_parse['src'], self.slither)
            self._events[event.full_name] = event

        self._eventsNotParsed = None

    def parse_state_variables(self):
        for father in self.inheritance_reverse:
            self._variables.update(father.variables_as_dict())
        '''print(self._variablesNotParsed)   #self._variablesNotParsed是个列表，每个元素是字典
            针对状态变量那一块
            [{'attributes': {'constant': False, 'name': 'credit', 'scope': 62, 'stateVariable': True, 'storageLocation': 'default', 'type': 'mapping(address => uint256)', 'value': None, 'visibility': 'public'}, 'children': [{'attributes': {'type': 'mapping(address => uint256)'}, 'children': [{'attributes': {'name': 'address', 'type': 'address'}, 'id': 2, 'name': 'ElementaryTypeName', 'src': '58:7:0'}, {'attributes': {'name': 'uint', 'type': 'uint256'}, 'id': 3, 'name': 'ElementaryTypeName', 'src': '69:4:0'}], 'id': 4, 'name': 'Mapping', 'src': '49:25:0'}], 'id': 5, 'name': 'VariableDeclaration', 'src': '49:39:0'}]
        '''
        for varNotParsed in self._variablesNotParsed:
            var = StateVariableSolc(varNotParsed)
            var.set_offset(varNotParsed['src'], self.slither)
            var.set_contract(self)
            self._variables[var.name] = var

    def analyze_constant_state_variables(self):
        from slither.solc_parsing.expressions.expression_parsing import VariableNotFound
        for var in self.variables:  #self.variables是爸爸Contract属性函数reurn:list(self.state_variables)。self.state_variables也是是爸爸Contract属性函数return:list(self._variables.values())
            if var.is_constant:
                # cant parse constant expression based on function calls
                #print('1111111111')
                try:
                    var.analyze(self)
                except VariableNotFound:
                    pass
        return

    def analyze_state_variables(self):
        #print(self.variables)  对于slither SimpleDAO.sol来说self.variables是[<slither.solc_parsing.variables.state_variable.StateVariableSolc object at 0x000002B0E2FBD198>]
        for var in self.variables:
            var.analyze(self)
        return

    def _parse_modifier(self, modifier):
        #print(str(modifier))
        modif = ModifierSolc(modifier, self)
        modif.set_contract(self)
        modif.set_offset(modifier['src'], self.slither)
        self._modifiers_no_params.append(modif)

    def parse_modifiers(self):

        for modifier in self._modifiersNotParsed:  #slither SimpleDAO.sol没到这
            self._parse_modifier(modifier)
        self._modifiersNotParsed = None

        return

    def _parse_function(self, function):
        func = FunctionSolc(function, self)  #function是一个大字典，根据这个字典的内容封装成FuntionSolc实例对象func
        func.set_offset(function['src'], self.slither)#根据src的值来对应到文件的行数
        self._functions_no_params.append(func)  #函数没有解析，self._functions_no_params列表就把这个函数对象加进去

    def parse_functions(self):
        #print(self._functionsNotParsed)
        for function in self._functionsNotParsed:# self._functionsNotParsed整体是一个列表，因为SimpleDAO.sol文件有三个函数，所以有三个字典元素。每个字典元素对应一个函数
            self._parse_function(function) #这个函数就在上面287行


        self._functionsNotParsed = None

        return

    def analyze_params_modifiers(self):
        for father in self.inheritance_reverse:
            self._modifiers.update(father.modifiers_as_dict())
        # print(self._modifiers_no_params)
        for modifier in self._modifiers_no_params:   # 对于slither SimpleDAO.sol这个self._modifiers_no_params为空[]
            modifier.analyze_params()
            self._modifiers[modifier.full_name] = modifier

        self._modifiers_no_params = []
        return

    def analyze_params_functions(self):
        # keep track of the contracts visited
        # to prevent an ovveride due to multiple inheritance of the same contract
        # A is B, C, D is C, --> the second C was already seen
        contracts_visited = []    #用来存储已经被访问过的contracts
        for father in self.inheritance_reverse:  #return reversed(self._inheritance),list(Contract): Inheritance list. Order: the last elem is the first father to be executed
            functions = {k:v for (k, v) in father.functions_as_dict().items()  #father.functions_as_dict()函数return self._functions.这是一个{}
                         if not v.contract in contracts_visited}   #v其实就是funtion对象.
            '''
                functions:挑出所有父合约的的函数，这些函数所在的合约并不在已经访问的合约contracts_visited = []列表中
            '''
            contracts_visited.append(father)#把每一个父合约添加到contracts_visited列表中
            self._functions.update(functions)   #把functions{k:v,k:v,....}给更新到self._functions
            '''
                 for function in self._functions_no_params:
                    self._functions[function.full_name] = function
            '''

        # If there is a constructor in the functions
        # We remove the previous constructor
        # As only one constructor is present per contracts
        #
        # Note: contract.all_functions_called returns the constructors of the base contracts
        has_constructor = False
        #print(self._functions_no_params)
        for function in self._functions_no_params:#self._functions_no_params是一个列表，这个列表存放了所有的函数对象
            function.analyze_params()  #此时已经遍历出每一个函数对象了，我们就去分析它的參數了
            if function.is_constructor:
                has_constructor = True

        if has_constructor:    #这个if的功能就是if这个合约对象有构造器函数那么，需要把构造器函数从self._functions中剔除出去
            _functions = {k:v for (k, v) in self._functions.items() if not v.is_constructor}
            self._functions = _functions

        for function in self._functions_no_params:
            self._functions[function.full_name] = function

        self._functions_no_params = []   #contract对象的这个列表属性用于存放所有的函数对象
        return

    def analyze_content_modifiers(self):
        for modifier in self.modifiers:
            modifier.analyze_content()
        return

    def analyze_content_functions(self):
        for function in self.functions:  #遍历Contract的实例对象的functions取出每一个function
            function.analyze_content()#对这每一个function对象进行内容的分析
        return

    def __hash__(self):
        return self._id
