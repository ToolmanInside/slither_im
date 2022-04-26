import logging
import os
import subprocess
import sys

from slither.detectors.abstract_detector import AbstractDetector, DetectorClassification
from slither.printers.abstract_printer import AbstractPrinter
from .solc_parsing.slitherSolc import SlitherSolc
from .utils.colors import red

# logger = logging.getLogger("Slither")
# logging.basicConfig(filename='../' +__name__+'.txt',filemode = 'a')

logger_detector = logging.getLogger("Detectors")
logger_printer = logging.getLogger("Printers")


class Slither(SlitherSolc):

    def __init__(self, contract, solc='solc', disable_solc_warnings=False, solc_arguments='', ast_format='--ast-json'):
        self._detectors = []    #def register_detector(self, detector_class):本文件第63行
        self._printers = []

        # json text provided
        if isinstance(contract, list):
            super(Slither, self).__init__('')
            for c in contract:
                if 'absolutePath' in c:
                    path = c['absolutePath']
                else:
                    path = c['attributes']['absolutePath']
                self._parse_contracts_from_loaded_json(c, path)
        # .json or .sol provided
        else:   #slither SimpleDAO.sol
            contracts_json = self._run_solc(contract, solc, disable_solc_warnings, solc_arguments, ast_format)#contract是文件名
            super(Slither, self).__init__(contract)   #调用SlitherSolc的

            for c in contracts_json:  #这个c就是solc --ast-json SimpleDAO.sol产生的json格式文件其实就是json字符串
                self._parse_contracts_from_json(c)   #这个函数在父类slitherSolc中实现  这个函数return true
                #print(c)
        self._analyze_contracts()

    @property
    def detectors(self):
        return self._detectors

    @property
    def detectors_high(self):
        return [d for d in self.detectors if d.IMPACT == DetectorClassification.HIGH]

    @property
    def detectors_medium(self):
        return [d for d in self.detectors if d.IMPACT == DetectorClassification.MEDIUM]

    @property
    def detectors_low(self):
        return [d for d in self.detectors if d.IMPACT == DetectorClassification.LOW]

    @property
    def detectors_informational(self):
        return [d for d in self.detectors if d.IMPACT == DetectorClassification.INFORMATIONAL]

    def register_detector(self, detector_class):
        """
        :param detector_class: Class inheriting from `AbstractDetector`.
        """
        self._check_common_things('detector', detector_class, AbstractDetector, self._detectors)

        instance = detector_class(self, logger_detector)
        self._detectors.append(instance)

    def register_printer(self, printer_class):
        """
        :param printer_class: Class inheriting from `AbstractPrinter`.
        """
        self._check_common_things('printer', printer_class, AbstractPrinter, self._printers)

        instance = printer_class(self, logger_printer)
        self._printers.append(instance)

    def run_detectors(self):
        """
        :return: List of registered detectors results.
        """

        return [d.detect() for d in self._detectors]

    def run_printers(self):
        """
        :return: List of registered printers outputs.
        """

        return [p.output(self.filename) for p in self._printers]

    def _check_common_things(self, thing_name, cls, base_cls, instances_list):

        if not issubclass(cls, base_cls) or cls is base_cls:
            raise Exception(
                "You can't register {!r} as a {}. You need to pass a class that inherits from {}".format(
                    cls, thing_name, base_cls.__name__
                )
            )

        if any(isinstance(obj, cls) for obj in instances_list):
            raise Exception(
                "You can't register {!r} twice.".format(cls)
            )

    def _run_solc(self, filename, solc, disable_solc_warnings, solc_arguments, ast_format):
        if not os.path.isfile(filename):   #SimpleDAO.sol不存在
            logger.error('{} does not exist (are you in the correct directory?)'.format(filename))
            exit(-1)
        is_ast_file = False
        if filename.endswith('json'):  # SimpleDAO.json就是ast
            is_ast_file = True
        elif not filename.endswith('.sol'): #不是.ast不是.json就raise Exception
            raise Exception('Incorrect file format')

        if is_ast_file:
            with open(filename) as astFile:
                stdout = astFile.read()
                if not stdout:
                    logger.info('Empty AST file: %s', filename)
                    sys.exit(-1)
                    #exit(results)
        else:  #如果is_ast_file = false也就是说filename.endwith('.so')=true
            cmd = [solc, filename, ast_format]  #拼凑产生solc --ast-json  SimpleDAO.sol这样一条命令
            if solc_arguments:  #如果solc_arguments不空
                # To parse, we first split the string on each '--'
                solc_args = solc_arguments.split('--')
                # Split each argument on the first space found
                # One solc option may have multiple argument sepparated with ' '
                # For example: --allow-paths /tmp .
                # split() removes the delimiter, so we add it again
                solc_args = [('--' + x).split(' ', 1) for x in solc_args if x]
                # Flat the list of list
                solc_args = [item for sublist in solc_args for item in sublist]
                cmd += solc_args
            # Add . as default allowed path
            if '--allow-paths' not in cmd:
                cmd += ['--allow-paths', '.']

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout, stderr = process.communicate()
            stdout, stderr = stdout.decode(), stderr.decode()  # convert bytestrings to unicode strings

            if stderr and (not disable_solc_warnings):  #如果编译产生错误
                stderr = stderr.split('\n')
                stderr = [x if 'Error' not in x else red(x) for x in stderr]
                stderr = '\n'.join(stderr)
                #logger.info('Compilation warnings/errors on %s:\n%s', filename, stderr)

        stdout = stdout.split('\n=')

        return stdout
