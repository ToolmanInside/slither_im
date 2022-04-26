from slither.core.cfg.node import NodeType
from slither.core.declarations import Function, SolidityFunction
from slither.core.expressions import UnaryOperation, UnaryOperationType
from slither.detectors.abstract_detector import (AbstractDetector,
                                                 DetectorClassification)
from slither.printers.abstract_printer import AbstractPrinter
from slither.visitors.expression.export_values import ExportValues
from slither.slithir.operations import (HighLevelCall, LowLevelCall,
                                        LibraryCall,
                                        Send, Transfer)
from slither.printers.summary.slithir import PrinterSlithIR
from slither.lcs.LCS_weight import LCS_weight
import re
from logzero import logger

class SignatureAbstraction(AbstractPrinter):
    ARGUMENT = 'signature-abstraction'
    HELP = 'Abstract Vulnerability Signatures'
    # lcs_weight = LCS_weight()

    def scan(self):
        self.result = {}
        self.visited_all_paths = {}   #self是指Reentrancy的实例
        logger.debug('Analyzing File: {}'.format(self.filename))
        for c in self.contracts:    #遍历所有的self.contracts列表取出每一个Contract对象
            if c.contract_kind == 'library':
                continue
            self.scan_file(c, self.filename)  #这个方法就在本文件156行左右

    def scan_file(self, contract, filename):
        initStateVar_name = []
        constructor_initStateVar_name = []
        otherFuncion_initStateVar_name = []
        for var in contract.variables:
            if var.initialized:
                initStateVar_name.append(var.name)
        for function in contract.functions:
            if function.is_constructor:
                for var in function.state_variables_written:
                    constructor_initStateVar_name.append(var.name)
        for function in contract.functions:
            if len(function._modifiers) or (function.visibility == 'private'):
                for var in function.state_variables_written:
                    otherFuncion_initStateVar_name.append(var.name)
        initStateVar_name.extend(constructor_initStateVar_name)
        initStateVar_name.extend(otherFuncion_initStateVar_name)
        logger.debug("Analyzing Contract: {}".format(contract.name))
        for function in contract.functions:
            logger.debug(f"Analyzing Function: {function.name}")

            function_ir = ""
            if function.contract == contract:
                for node in function.nodes:
                    target_address_is_constant = False
                    for x in node.state_variables_read:  
                        if (x.is_constant):
                            target_address_is_constant = True
                    if target_address_is_constant:  # 如果这个节点中所有的读的全局变量都是常量跳过这个节点
                        continue
                    if node.expression:
                        # function_ir = function_ir + ' Expression: {}'.format("expressionToken")
                        # function_ir += ' IRs:'
                        for ir in node.irs:
                            function_ir += ' {}'.format(ir)

            function_ir += ' '
            for varname in initStateVar_name:
                #compilePattern = 'dest:'+varname+'.*?\s function:.+?\sarguments:\[.*?] value:.+?\s'
                initVarPattern = re.compile('dest:'+varname+'.*?\sfunction:.+?\sarguments:\[.*?]')
                function_ir = re.sub(initVarPattern, "initVar", function_ir)
                destTMPlist = re.findall('(TMP_[0-9]+) = CONVERT '+varname+' to', function_ir)
                for destTMP in destTMPlist:
                    initVarPatternConvert = re.compile('dest:'+destTMP+'.*?\sfunction:.+?\sarguments:\[.*?]')
                    function_ir = re.sub(initVarPatternConvert, "initVar", function_ir)
                destSecondlist = re.findall('TMP_[0-9]+ = CONVERT ' + varname + ' to .+?\s([a-zA-Z_$0-9\.]+)\(.+?\) := TMP_[0-9]+\(.+?\)', function_ir)
                for destSecond in destSecondlist:
                    initSecondVarPattern = re.compile(
                        'dest:' + destSecond + '\([a-zA-Z_$0-9\.]+\),*\sfunction:.+?\sarguments:\[.*?]')
                    function_ir = re.sub(initSecondVarPattern, 'initVar', function_ir)
            print(f"IR: {function_ir}")

    def output(self, _filename):
        self.scan()
        self.info("")
        return