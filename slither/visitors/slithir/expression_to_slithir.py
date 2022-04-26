import logging

from slither.core.declarations import Function, Structure
from slither.core.expressions import (AssignmentOperationType,
                                      UnaryOperationType)
from slither.core.solidity_types.array_type import ArrayType
from slither.slithir.operations import (Assignment, Binary, BinaryType, Delete,
                                        Index, InitArray, InternalCall, Member,
                                        NewArray, NewContract, NewStructure,
                                        TypeConversion, Unary, Unpack, Return)
from slither.slithir.tmp_operations.argument import Argument
from slither.slithir.tmp_operations.tmp_call import TmpCall
from slither.slithir.tmp_operations.tmp_new_array import TmpNewArray
from slither.slithir.tmp_operations.tmp_new_contract import TmpNewContract
from slither.slithir.tmp_operations.tmp_new_elementary_type import \
    TmpNewElementaryType
from slither.slithir.tmp_operations.tmp_new_structure import TmpNewStructure
from slither.slithir.variables import (Constant, ReferenceVariable,
                                       TemporaryVariable, TupleVariable)
from slither.visitors.expression.expression import ExpressionVisitor

logger = logging.getLogger("VISTIOR:ExpressionToSlithIR")

key = 'expressionToSlithIR'

def get(expression):
    val = expression.context[key]
    # we delete the item to reduce memory use
    #print(val)
    '''
        credit
        to
        REF_0
        msg.value
        credit
        to
        REF_1
        credit
        msg.sender
        REF_2
        amount
        msg.sender
        REF_3
        REF_4
        amount
        TMP_2
        require(bool)
        TMP_4
        credit
        msg.sender
        REF_5
        amount
    '''
    #print(str(type(val)))
    '''
        <class 'slither.solc_parsing.variables.state_variable.StateVariableSolc'>
        <class 'slither.solc_parsing.variables.local_variable.LocalVariableSolc'>
        <class 'slither.slithir.variables.reference.ReferenceVariable'>
        <class 'slither.core.declarations.solidity_variables.SolidityVariableComposed'>
        <class 'slither.solc_parsing.variables.state_variable.StateVariableSolc'>
        <class 'slither.solc_parsing.variables.local_variable.LocalVariableSolc'>
        <class 'slither.slithir.variables.reference.ReferenceVariable'>
        <class 'slither.solc_parsing.variables.state_variable.StateVariableSolc'>
        <class 'slither.core.declarations.solidity_variables.SolidityVariableComposed'>
        <class 'slither.slithir.variables.reference.ReferenceVariable'>
        <class 'slither.solc_parsing.variables.local_variable.LocalVariableSolc'>
        <class 'slither.core.declarations.solidity_variables.SolidityVariableComposed'>
        <class 'slither.slithir.variables.reference.ReferenceVariable'>
        <class 'slither.slithir.variables.reference.ReferenceVariable'>
        <class 'slither.solc_parsing.variables.local_variable.LocalVariableSolc'>
        <class 'slither.slithir.variables.temporary.TemporaryVariable'>
        <class 'slither.core.declarations.solidity_variables.SolidityFunction'>
        <class 'slither.slithir.variables.temporary.TemporaryVariable'>
        <class 'slither.solc_parsing.variables.state_variable.StateVariableSolc'>
        <class 'slither.core.declarations.solidity_variables.SolidityVariableComposed'>
        <class 'slither.slithir.variables.reference.ReferenceVariable'>
        <class 'slither.solc_parsing.variables.local_variable.LocalVariableSolc'>
    '''
    del expression.context[key]
    return val

def set_val(expression, val):
    expression.context[key] = val

def convert_assignment(left, right, t, return_type):
    if t == AssignmentOperationType.ASSIGN:
        return Assignment(left, right, return_type)
    elif t == AssignmentOperationType.ASSIGN_OR:
        return Binary(left, left, right, BinaryType.OR)
    elif t == AssignmentOperationType.ASSIGN_CARET:
        return Binary(left, left, right, BinaryType.CARET)
    elif t == AssignmentOperationType.ASSIGN_AND:
        return Binary(left, left, right, BinaryType.AND)
    elif t == AssignmentOperationType.ASSIGN_LEFT_SHIFT:
        return Binary(left, left, right, BinaryType.LEFT_SHIFT)
    elif t == AssignmentOperationType.ASSIGN_RIGHT_SHIFT:
        return Binary(left, left, right, BinaryType.RIGHT_SHIFT)
    elif t == AssignmentOperationType.ASSIGN_ADDITION:
        return Binary(left, left, right, BinaryType.ADDITION)#形参：def __init__(self, result, left_variable, right_variable, operation_type):
    elif t == AssignmentOperationType.ASSIGN_SUBTRACTION:
        return Binary(left, left, right, BinaryType.SUBTRACTION)
    elif t == AssignmentOperationType.ASSIGN_MULTIPLICATION:
        return Binary(left, left, right, BinaryType.MULTIPLICATION)
    elif t == AssignmentOperationType.ASSIGN_DIVISION:
        return Binary(left, left, right, BinaryType.DIVISION)
    elif t == AssignmentOperationType.ASSIGN_MODULO:
        return Binary(left, left, right, BinaryType.MODULO)

    logger.error('Missing type during assignment conversion')
    exit(-1)

class ExpressionToSlithIR(ExpressionVisitor):

    def __init__(self, expression, node):
        from slither.core.cfg.node import NodeType
        self._expression = expression
        self._node = node
        self._result = []
        self._visit_expression(self.expression) # return self._expression
        if node.type == NodeType.RETURN:
            self._result.append(Return(get(self.expression)))  # get:val = expression.context[key] return val
        for ir in self._result:
            ir.set_node(node)

    def result(self):
        return self._result

    def _post_assignement_operation(self, expression):
        left = get(expression.expression_left)
        right = get(expression.expression_right)
        if isinstance(left, list): # tuple expression: 元组
            #print("1111111111111111") slither SimpleDAO.sol没有进来
            if isinstance(right, list): # unbox assigment  拆箱
                assert len(left) == len(right)
                for idx in range(len(left)):
                    if not left[idx] is None:
                        operation = convert_assignment(left[idx], right[idx], expression.type, expression.expression_return_type)
                        self._result.append(operation)
                set_val(expression, None)
            else:
                assert isinstance(right, TupleVariable)
                for idx in range(len(left)):
                    if not left[idx] is None:
                        operation = Unpack(left[idx], right, idx)
                        self._result.append(operation)
                set_val(expression, None)
        else:
            # Init of array, like
            # uint8[2] var = [1,2];
            if isinstance(right, list):
                #print("222222222222") slither SimpleDAO.sol没有进来
                operation = InitArray(right, left)
                self._result.append(operation)
                set_val(expression, left)
            else:
                #print(left)
                '''
                REF_0
                REF_5
                '''
                #print(str(type(left)))
                '''
                    <class 'slither.slithir.variables.reference.ReferenceVariable'>
                    <class 'slither.slithir.variables.reference.ReferenceVariable'>
                '''
                operation = convert_assignment(left, right, expression.type, expression.expression_return_type)#本文件85行，expression.type=AssignmentOperationType.ASSIGN_ADDITION
                #print(operation)
                '''
                REF_0(None) = REF_0 + msg.value
                REF_5(None) = REF_5 - amount
                '''
                self._result.append(operation)
                # Return left to handle
                # a = b = 1; 
                set_val(expression, left)

    def _post_binary_operation(self, expression):
        left = get(expression.expression_left)
        right = get(expression.expression_right)
        val = TemporaryVariable(self._node)

        operation = Binary(val, left, right, expression.type)
        #print(operation)
        '''
        TMP_0(bool) = REF_2 >= amount
        '''
        self._result.append(operation)
        set_val(expression, val)

    def _post_call_expression(self, expression):
        called = get(expression.called)
        args = [get(a) for a in expression.arguments if a]
        for arg in args:
            arg_ = Argument(arg)
            self._result.append(arg_)
        if isinstance(called, Function):
            #print("11111111111111111") #没进
            # internal call

            # If tuple
            if expression.type_call.startswith('tuple(') and expression.type_call != 'tuple()':
                #print("222222222222")
                val = TupleVariable()
            else:
                val = TemporaryVariable(self._node)
            internal_call = InternalCall(called, len(args), val, expression.type_call)
            self._result.append(internal_call)
            set_val(expression, val)
        else:
            #print("11111111111111111")
            '''
            11111111111111111
            11111111111111111
            11111111111111111
            '''
            val = TemporaryVariable(self._node)

            # If tuple
            if expression.type_call.startswith('tuple(') and expression.type_call != 'tuple()':
                #print("33333333333333333333")#没进
                val = TupleVariable()
            else:
                val = TemporaryVariable(self._node)

            message_call = TmpCall(called, len(args), val, expression.type_call)
            #print(message_call)
            '''
            TMP_2 = TMPCALL1 REF_4
            TMP_4 = TMPCALL0 TMP_2  
            TMP_6 = TMPCALL1 require(bool)
            '''
            self._result.append(message_call)
            set_val(expression, val)

    def _post_conditional_expression(self, expression):
        raise Exception('Ternary operator are not convertible to SlithIR {}'.format(expression))

    def _post_elementary_type_name_expression(self, expression):
        set_val(expression, expression.type)

    def _post_identifier(self, expression):
        set_val(expression, expression.value)

    def _post_index_access(self, expression):
        left = get(expression.expression_left)
        right = get(expression.expression_right)
        val = ReferenceVariable(self._node)
        operation = Index(val, left, right, expression.type)
        #print(operation)
        '''
        REF_0(None) -> credit[to]
        REF_1(None) -> credit[to]
        REF_2(None) -> credit[msg.sender]
        REF_5(None) -> credit[msg.sender]
        '''
        self._result.append(operation)
        set_val(expression, val)

    def _post_literal(self, expression):
        set_val(expression, Constant(expression.value))

    def _post_member_access(self, expression):
        expr = get(expression.expression)
        val = ReferenceVariable(self._node)
        member = Member(expr, Constant(expression.member_name), val)
        self._result.append(member)
        set_val(expression, val)

    def _post_new_array(self, expression):
        val = TemporaryVariable(self._node)
        operation = TmpNewArray(expression.depth, expression.array_type, val)
        self._result.append(operation)
        set_val(expression, val)

    def _post_new_contract(self, expression):
        val = TemporaryVariable(self._node)
        operation = TmpNewContract(expression.contract_name, val)
        self._result.append(operation)
        set_val(expression, val)

    def _post_new_elementary_type(self, expression):
        # TODO unclear if this is ever used?
        val = TemporaryVariable(self._node)
        operation = TmpNewElementaryType(expression.type, val)
        self._result.append(operation)
        set_val(expression, val)

    def _post_tuple_expression(self, expression):
        expressions = [get(e) if e else None for e in expression.expressions]
        if len(expressions) == 1:
            val = expressions[0]
        else:
            val = expressions
        set_val(expression, val)

    def _post_type_conversion(self, expression):
        expr = get(expression.expression)
        val = TemporaryVariable(self._node)
        operation = TypeConversion(val, expr, expression.type)
        self._result.append(operation)
        set_val(expression, val)

    def _post_unary_operation(self, expression):
        value = get(expression.expression)
        if expression.type in [UnaryOperationType.BANG, UnaryOperationType.TILD]:
            lvalue = TemporaryVariable(self._node)
            operation = Unary(lvalue, value, expression.type)
            self._result.append(operation)
            set_val(expression, lvalue)
        elif expression.type in [UnaryOperationType.DELETE]:
            operation = Delete(value)
            self._result.append(operation)
            set_val(expression, value)
        elif expression.type in [UnaryOperationType.PLUSPLUS_PRE]:
            operation = Binary(value, value, Constant("1"), BinaryType.ADDITION)
            self._result.append(operation)
            set_val(expression, value)
        elif expression.type in [UnaryOperationType.MINUSMINUS_PRE]:
            operation = Binary(value, value, Constant("1"), BinaryType.SUBTRACTION)
            self._result.append(operation)
            set_val(expression, value)
        elif expression.type in [UnaryOperationType.PLUSPLUS_POST]:
            lvalue = TemporaryVariable(self._node)
            operation = Assignment(lvalue, value, value.type)
            self._result.append(operation)
            operation = Binary(value, value, Constant("1"), BinaryType.ADDITION)
            self._result.append(operation)
            set_val(expression, lvalue)
        elif expression.type in [UnaryOperationType.MINUSMINUS_POST]:
            lvalue = TemporaryVariable(self._node)
            operation = Assignment(lvalue, value, value.type)
            self._result.append(operation)
            operation = Binary(value, value, Constant("1"), BinaryType.SUBTRACTION)
            self._result.append(operation)
            set_val(expression, lvalue)
        elif expression.type in [UnaryOperationType.PLUS_PRE]:
            set_val(expression, value)
        elif expression.type in [UnaryOperationType.MINUS_PRE]:
            lvalue = TemporaryVariable(self._node)
            operation = Binary(lvalue, Constant("0"), value, BinaryType.SUBTRACTION)
            self._result.append(operation)
            set_val(expression, lvalue)
        else:
            raise Exception('Unary operation to IR not supported {}'.format(expression))

