#__*__ coding: utf-8 __*__
import os
import json
import re
import logging

logger = logging.getLogger("SlitherSolcParsing")

from slither.solc_parsing.declarations.contract import ContractSolc04
from slither.core.slither_core import Slither
from slither.core.declarations.pragma_directive import Pragma
from slither.core.declarations.import_directive import Import

class SlitherSolc(Slither):

    def __init__(self, filename):
        super(SlitherSolc, self).__init__()  #调用from slither.core.slither_core import Slither的Slither的_init_()
        self._filename = filename
        self._contractsNotParsed = []
        self._contracts_by_id = {}
        self._analyzed = False

        self._is_compact_ast = False

    def get_key(self):
        if self._is_compact_ast:
            return 'nodeType'
        return 'name'

    def get_children(self):
        if self._is_compact_ast:
            return 'nodes'
        return 'children'

    @property
    def is_compact_ast(self):
        return self._is_compact_ast

    def _parse_contracts_from_json(self, json_data):
        try:
            data_loaded = json.loads(json_data)  #对solc --ast-json SimpleDAO.sol 产生的json格式的ast文件进行加载：data_loaded是字典类型
            self._parse_contracts_from_loaded_json(data_loaded['ast'], data_loaded['sourcePath'])  #:prama data_loaded['ast'] = ast的json的字典  data_loaded['sourcePath'] = '=====SimpleDAO.sol=========='
            return True 
        except ValueError:

            first = json_data.find('{')
            if first != -1:
                last = json_data.rfind('}') + 1
                filename = json_data[0:first]
                json_data = json_data[first:last]

                data_loaded = json.loads(json_data)
                self._parse_contracts_from_loaded_json(data_loaded, filename)
                return True
            return False

    def _parse_contracts_from_loaded_json(self, data_loaded, filename):   #:prama data_loaded = ast的json的字典  filename = '=====SimpleDAO.sol=========='他的调用者就在上方
        '''
        #self._source_units = {0:'SimpleDAO.sol'}被得到
        #self.source_code{'SimpDAO.sol':SimpDAO.sol源代码}被得到
         self._contractsNotParsed.append(contract)被得到
        '''
        if 'nodeType' in data_loaded:
            self._is_compact_ast = True

        if 'sourcePaths' in data_loaded:  #对于slither SimpleDAO.sol这个if没有执行
            #print('11111')
            for sourcePath in data_loaded['sourcePaths']:
                if os.path.isfile(sourcePath):
                    with open(sourcePath) as f:
                        source_code = f.read()
                    self.source_code[sourcePath] = source_code

        if data_loaded[self.get_key()] == 'root':  #0.4以上的name是"SourceUnite"
            self._solc_version = '0.3'
            logger.error('solc <0.4 is not supported')
            return
        elif data_loaded[self.get_key()] == 'SourceUnit':
            self._solc_version = '0.4'
            #print(data_loaded)
            #print(filename)
            self._parse_source_unit(data_loaded, filename)  #:prama data_loaded=ast的json的字典 filename = '=====SimpleDAO.sol=========='
            #self._source_units = {0:'SimpleDAO.sol'}已得到
            #self.source_code{'SimpDAO.sol':SimpDAO.sol源代码}已得到
        else:
            logger.error('solc version is not supported')
            return

        for contract_data in data_loaded[self.get_children()]:   #这个函数就在上边self.get_children = 'children' ，data_loaded[self.get_children()]是一个这样的列表[{},{}]
            #print(str(type(contract_data)))
            '''每一个contract_data都是一个字典'''
            # if self.solc_version == '0.3':
            #     assert contract_data[self.get_key()] == 'Contract'
            #     contract = ContractSolc03(self, contract_data)
            if self.solc_version == '0.4':  #没错
                assert contract_data[self.get_key()] in ['ContractDefinition', 'PragmaDirective', 'ImportDirective']
                if contract_data[self.get_key()] == 'ContractDefinition':   #self.get_key()返回的是'name' self.getkey()也在本文件上面
                    contract = ContractSolc04(self, contract_data)  #contract_data是一个这样的字典{'attributes':xxxxxx, 'children':[xxx,xxxx,....], 'id':xxx, 'name':'ContractDefinition', 'src':xxx}
                    if 'src' in contract_data:
                        contract.set_offset(contract_data['src'], self)  #对于slither SimpleDAO.so来说 此时contract_data['src']=''26:398:0''
                        '''
                        print(contract):  SimpleDAO
                        print(str(type(contract))):  <class 'slither.solc_parsing.declarations.contract.ContractSolc04'>
                        print(str(contract)):  SimpleDAO
                        '''
                    self._contractsNotParsed.append(contract)
                elif contract_data[self.get_key()] == 'PragmaDirective':
                    if self._is_compact_ast:
                        pragma = Pragma(contract_data['literals'])
                    else:
                        pragma = Pragma(contract_data['attributes']["literals"])   #contract_data['attributes']["literals"]=['solidity', '^', '0.4', '.24']
                    pragma.set_offset(contract_data['src'], self)
                    self._pragma_directives.append(pragma)
                elif contract_data[self.get_key()] == 'ImportDirective':
                    if self.is_compact_ast:
                        import_directive = Import(contract_data["absolutePath"])
                    else:
                        import_directive = Import(contract_data['attributes']["absolutePath"])
                    import_directive.set_offset(contract_data['src'], self)
                    self._import_directives.append(import_directive)


    def _parse_source_unit(self, data, filename):  #:prama data=ast的json的字典 filename = '=====SimpleDAO.sol=========='
        '''

        :param data:
        :param filename:
        :return:
        这个函数得到了这两个字典
        self._source_units = {0:'SimpleDAO.sol'}   这个self就是Slither对象
        self.source_code{'SimpDAO.sol':SimpDAO.sol源代码}

        '''
        #print(data)
        if data[self.get_key()] != 'SourceUnit':
            return -1  # handle solc prior 0.3.6

        # match any char for filename
        # filename can contain space, /, -, ..
        name = re.findall('=* (.+) =*', filename) # name = ['SimpleDAO.sol']
        if name:
            assert len(name) == 1
            name = name[0]
        else:
            name = filename

        sourceUnit = -1  # handle old solc, or error
        if 'src' in data:
            #print(data['src'])
            sourceUnit = re.findall('[0-9]*:[0-9]*:([0-9]*)', data['src']) #对于Slither SimpleDAO.sol中data['src']=0:424:0
            #print(sourceUnit)
            if len(sourceUnit) == 1: #sourceUnit=['0']
                sourceUnit = int(sourceUnit[0]) #sourceUnit=0

        self._source_units[sourceUnit] = name # sourceUnit = 0  name='SimpleDAO.sol'
        if os.path.isfile(name) and not name in self.source_code: #'SimeDAO,sol'不在self.source_code中,slither SimpleDAO.sol这里是执行的
            with open(name,errors='ignore') as f:
                source_code = f.read() #source_code就是标准的SimpleDAO.sol源代码
                #print(source_code)
            self.source_code[name] = source_code #self.source_code{'SimpDAO.sol':SimpDAO.sol源代码}
        else:             #对于slither SimpleDAO.sol这块没有执行
            lib_name = os.path.join('node_modules', name)
            if os.path.isfile(lib_name) and not name in self.source_code: #'SimeDAO,sol'不在self.source_code中
                with open(lib_name) as f:
                    source_code = f.read()
                self.source_code[name] = source_code


    def _analyze_contracts(self):
        '''
        self._contracts_by_id[contract.id] = contract  self._contracts_by_id={62:contract}被得到
        self._contracts[contract.name] = contract      self._contracts={'SimpleDAO.sol':contract}被得到
        :return:
        '''
        if self._analyzed:  #类的__init__(self, filename):中声明了self._analyzed=false
            raise Exception('Contract analysis can be run only once!')

        # First we save all the contracts in a dict
        # the key is the contractid
        for contract in self._contractsNotParsed:#这块执行了
            #print(contract.name)
            #print(contract.id)
            if contract.name in self._contracts:  #这块代码没有被执行  contract.name = 'SimpleDAO' ; 字典self._contracts{contract.name:contract}
                if contract.id != self._contracts[contract.name].id: #contract.id=62
                    info = 'Slither does not handle projects with contract names re-use'
                    info += '\n{} is defined in:'.format(contract.name)
                    info += '\n- {}\n- {}'.format(contract.source_mapping_str,
                                               self._contracts[contract.name].source_mapping_str)
                    logger.error(info)
                    exit(-1)
            else:
                self._contracts_by_id[contract.id] = contract
                self._contracts[contract.name] = contract  #在爷爷Slither里面声明的属性

        # Update of the inheritance 
        for contract in self._contractsNotParsed:   #self._contractsNotParsed是class SlitherSolc(Slither)一开头就声明的列表
            # remove the first elem in linearizedBaseContracts as it is the contract itself
            fathers = []
            #print(contract.linearizedBaseContracts[1:])
            #print(contract.remapping)
            for i in contract.linearizedBaseContracts[1:]:  #不执行因为对于slither SimpleDAO.sol来说contract.linearizedBaseContracts[1:]为空[]
                if i in contract.remapping:#对于slither SimpleDAO.sol来说contract.remapping为空{}
                    fathers.append(self.get_contract_from_name(contract.remapping[i]))
                else:
                    fathers.append(self._contracts_by_id[i])
            contract.setInheritance(fathers)
        #print(self.contracts)
        contracts_to_be_analyzed = self.contracts #self.contracts是一个列表，其实就是list(self._contracts.values)，对于slither SimpleDAO.sol来说self.contracts=[<slither.solc_parsing.declarations.contract.ContractSolc04 object at 0x00000207DFCC5DA0>]

        # Any contract can refer another contract enum without need for inheritance
        self._analyze_all_enums(contracts_to_be_analyzed) #这个方法在本文件240行这个方法就在下边不远处，contracts_to_be_analyzed其实就是一个存储contract对象（这个对象封装了SimpleDAO.sol的一些信息）的一个列表，._analyze_all_enums这个分析对slither SimpleDAO没有可分析的内容
        [c.set_is_analyzed(False) for c in self.contracts]

        libraries = [c for c in contracts_to_be_analyzed if c.contract_kind == 'library']  #合约种类分为library和普通的contract
        contracts_to_be_analyzed = [c for c in contracts_to_be_analyzed if c.contract_kind != 'library']

        # We first parse the struct/variables/functions/contract
        self._analyze_first_part(contracts_to_be_analyzed, libraries)  #这个方法在248行  struce, var, modifier
        [c.set_is_analyzed(False) for c in self.contracts]

        # We analyze the struct and parse and analyze the events
        # A contract can refer in the variables a struct or a event from any contract
        # (without inheritance link)
        self._analyze_second_part(contracts_to_be_analyzed, libraries)
        [c.set_is_analyzed(False) for c in self.contracts]

        # Then we analyse state variables, functions and modifiers
        self._analyze_third_part(contracts_to_be_analyzed, libraries)   #在本文件295行

        self._analyzed = True

        self._convert_to_slithir()

    # TODO refactor the following functions, and use a lambda function

    @property
    def analyzed(self):
        return self._analyzed  #这是个bool

    def _analyze_all_enums(self, contracts_to_be_analyzed):
        while contracts_to_be_analyzed:
            contract = contracts_to_be_analyzed[0]

            contracts_to_be_analyzed = contracts_to_be_analyzed[1:]#因为我们只是分析单个（slither SimpleDAO.sol）所以此时为空了
            all_father_analyzed = all(father.is_analyzed for father in contract.inheritance)

            if not contract.inheritance or all_father_analyzed:  #如果contract的爸爸是空或者它所有的爸爸都分析过了
                self._analyze_enums(contract)  #这个方法在311行
            else:
                contracts_to_be_analyzed += [contract]
        return

    def _analyze_first_part(self, contracts_to_be_analyzed, libraries):
        for lib in libraries:    #对于libirary暂时不看
            self._parse_struct_var_modifiers_functions(lib)

        # Start with the contracts without inheritance
        # Analyze a contract only if all its fathers
        # Were analyzed
        while contracts_to_be_analyzed:

            contract = contracts_to_be_analyzed[0]  #拿出来列表读一个准备去分析

            contracts_to_be_analyzed = contracts_to_be_analyzed[1:]
            all_father_analyzed = all(father.is_analyzed for father in contract.inheritance)

            if not contract.inheritance or all_father_analyzed:  #如果此时的这个contract的爸爸为空或者它的爸爸都被分析过了
                self._parse_struct_var_modifiers_functions(contract)  #这个函数在316行

            else:
                contracts_to_be_analyzed += [contract]
        return

    def _analyze_second_part(self, contracts_to_be_analyzed, libraries):
        for lib in libraries:
            self._analyze_struct_events(lib)

        # Start with the contracts without inheritance
        # Analyze a contract only if all its fathers
        # Were analyzed
        while contracts_to_be_analyzed:

            contract = contracts_to_be_analyzed[0]

            contracts_to_be_analyzed = contracts_to_be_analyzed[1:]
            all_father_analyzed = all(father.is_analyzed for father in contract.inheritance)

            if not contract.inheritance or all_father_analyzed:
                self._analyze_struct_events(contract)

            else:
                contracts_to_be_analyzed += [contract]
        return

    def _analyze_third_part(self, contracts_to_be_analyzed, libraries):
        for lib in libraries:
            self._analyze_variables_modifiers_functions(lib)

        # Start with the contracts without inheritance
        # Analyze a contract only if all its fathers
        # Were analyzed
        while contracts_to_be_analyzed:

            contract = contracts_to_be_analyzed[0]

            contracts_to_be_analyzed = contracts_to_be_analyzed[1:]#从[1:]合约将要去分析
            all_father_analyzed = all(father.is_analyzed for father in contract.inheritance)#如果本合约的所有爸爸father.is_analyzed==true.则all_father_analyzed==true

            if not contract.inheritance or all_father_analyzed:#如果本合约没有父亲或者本合约的父亲都被分析过了
                self._analyze_variables_modifiers_functions(contract)#本文件341行   去分析contract对象的variable,modifiers，functions

            else:
                contracts_to_be_analyzed += [contract]
        return

    def _analyze_enums(self, contract):
        # Enum must be analyzed first
        contract.analyze_enums()
        contract.set_is_analyzed(True)

    def _parse_struct_var_modifiers_functions(self, contract):
        contract.parse_structs()  # struct can refer another struct #对于slither SimpleDAO.sol没什么可解析的因为源代码里面就没有结构体
        contract.parse_state_variables()
        contract.parse_modifiers()
        contract.parse_functions()
        contract.set_is_analyzed(True)

    def _analyze_struct_events(self, contract):

        contract.analyze_constant_state_variables()  # slither SimpleDAO.solh什么都没有做

        # Struct can refer to enum, or state variables
        contract.analyze_structs()
        # Event can refer to struct
        contract.analyze_events()

        contract.analyze_using_for()  # slither SimpleDAO.sol什么都没有做

        contract.set_is_analyzed(True)

    def _analyze_variables_modifiers_functions(self, contract):
        # State variables, modifiers and functions can refer to anything

        contract.analyze_params_modifiers()  # slither SimpleDAO.solh什么都没有做
        contract.analyze_params_functions()  # 分析函数的參數,LocalVariables

        contract.analyze_state_variables()

        contract.analyze_content_modifiers()
        contract.analyze_content_functions()

        contract.set_is_analyzed(True)

    def _convert_to_slithir(self):
        for contract in self.contracts:
            #print(contract.functions + contract.modifiers)
            for func in contract.functions + contract.modifiers:  # 对于slither SimpleDAO只有contract.functions=[<slither.solc_parsing.declarations.function.FunctionSolc object at 0x000002976EF35C50>, <slither.solc_parsing.declarations.function.FunctionSolc object at 0x000002976EF35D68>, <slither.solc_parsing.declarations.function.FunctionSolc object at 0x000002976EF35C88>]，contract.modifiers为空
                if func.contract == contract:
                    func.convert_expression_to_slithir()
