"""
    Module detecting state uninitialized variables
    Recursively check the called functions

    The heuristic checks:
    - state variables including mappings/refs
    - LibraryCalls, InternalCalls, InternalDynamicCalls with storage variables

    Only analyze "leaf" contracts (contracts that are not inherited by another contract)
"""

from slither.detectors.abstract_detector import AbstractDetector, DetectorClassification
from slither.core.variables.state_variable import StateVariable
from slither.slithir.variables import ReferenceVariable
from slither.slithir.operations.assignment import Assignment

from slither.slithir.operations import (OperationWithLValue, Index, Member,
                                        InternalCall, InternalDynamicCall, LibraryCall)


class UninitializedStateVarsDetection(AbstractDetector):
    """
    Constant function detector
    """

    ARGUMENT = 'uninitialized-state'
    HELP = 'Uninitialized state variables'
    IMPACT = DetectorClassification.HIGH
    CONFIDENCE = DetectorClassification.HIGH

    WIKI = 'https://github.com/trailofbits/slither/wiki/Vulnerabilities-Description#uninitialized-state-variables'

    @staticmethod
    def written_variables(contract):
        ret = []
        for f in contract.all_functions_called + contract.modifiers:
            for n in f.nodes:
                ret += n.state_variables_written
                for ir in n.irs:
                    if isinstance(ir, LibraryCall) \
                            or isinstance(ir, InternalCall):
                        idx = 0
                        if ir.function:
                            for param in ir.function.parameters:
                                if param.location == 'storage':
                                    ret.append(ir.arguments[idx])
                                idx = idx+1

        return ret

    @staticmethod
    def read_variables(contract):
        ret = []
        for f in contract.all_functions_called + contract.modifiers:
            ret += f.state_variables_read
        return ret

    def detect_uninitialized(self, contract):
        written_variables = self.written_variables(contract)
        read_variables = self.read_variables(contract)
        return [(variable, contract.get_functions_reading_from_variable(variable))
                for variable in contract.state_variables if variable not in written_variables and\
                                                            not variable.expression and\
                                                            variable in read_variables]

    def detect(self):
        """ Detect uninitialized state variables

        Recursively visit the calls
        Returns:
            dict: [contract name] = set(state variable uninitialized)
        """
        results = []
        for c in self.slither.contracts_derived:
            ret = self.detect_uninitialized(c)
            for variable, functions in ret:
                info = "\t{}.{} ({}) is never initialized. It is used in:\n"
                info = info.format(variable.contract.name,
                                   variable.name,
                                   variable.source_mapping_str)
                for f in functions:
                    info += "\t\tUninitialized-state in {}.{} ({})\n".format(f.contract.name, f.name, f.source_mapping_str)
                self.log(info)

                source = [variable.source_mapping]
                source += [f.source_mapping for f in functions]

                json = self.generate_json_result(info)
                self.add_variable_to_json(variable, json)
                self.add_functions_to_json(functions, json)
                results.append(json)

        return results
