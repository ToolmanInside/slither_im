
from slither.visitors.expression.expression import ExpressionVisitor

from slither.core.expressions.assignment_operation import AssignmentOperationType

from slither.core.variables.variable import Variable

key = 'FindCall'

def get(expression):
    val = expression.context[key]
    # we delete the item to reduce memory use
    del expression.context[key]
    return val

def set_val(expression, val):   #val=called+args+[expression]
    expression.context[key] = val

class FindCalls(ExpressionVisitor):

    def result(self):
        if self._result is None:
            self._result = list(set(get(self.expression)))
        return self._result

    def _post_assignement_operation(self, expression):
        left = get(expression.expression_left)
        right = get(expression.expression_right)
        val = left + right
        set_val(expression, val)

    def _post_binary_operation(self, expression):
        left = get(expression.expression_left)
        right = get(expression.expression_right)
        val = left + right
        set_val(expression, val)

    def _post_call_expression(self, expression):
        called = get(expression.called)
        #print(called)
        '''
        []
        [<slither.core.expressions.call_expression.CallExpression object at 0x000001ACF47D8630>]
        []
        '''
        args = [get(a) for a in expression.arguments if a]
        #print(args)
        '''
        [[]]
        []
        [[<slither.core.expressions.call_expression.CallExpression object at 0x00000179FF318630>, <slither.core.expressions.call_expression.CallExpression object at 0x00000179FF331240>]]
        '''
        args = [item for sublist in args for item in sublist]
        #print(args)
        '''
        []
        []
        [<slither.core.expressions.call_expression.CallExpression object at 0x00000163353B8630>, <slither.core.expressions.call_expression.CallExpression object at 0x00000163353D0240>]
        '''
        val = called + args
        #print(val)
        '''
        
        []
        [<slither.core.expressions.call_expression.CallExpression object at 0x00000253C70F8630>]
        [<slither.core.expressions.call_expression.CallExpression object at 0x00000253C70F8630>, <slither.core.expressions.call_expression.CallExpression object at 0x00000253C7111240>]
        '''
        val += [expression]
        #print(val)
        '''
        [<slither.core.expressions.call_expression.CallExpression object at 0x0000027B30498630>]
        [<slither.core.expressions.call_expression.CallExpression object at 0x0000027B30498630>, <slither.core.expressions.call_expression.CallExpression object at 0x0000027B304B0240>]
        [<slither.core.expressions.call_expression.CallExpression object at 0x0000027B30498630>, <slither.core.expressions.call_expression.CallExpression object at 0x0000027B304B0240>, <slither.core.expressions.call_expression.CallExpression object at 0x0000027B304987B8>]
        '''
        set_val(expression, val)  #val=called+args+[expression]

    def _post_conditional_expression(self, expression):
        if_expr = get(expression.if_expression)
        else_expr = get(expression.else_expression)
        then_expr = get(expression.then_expression)
        val = if_expr + else_expr + then_expr
        set_val(expression, val)

    def _post_elementary_type_name_expression(self, expression):
        set_val(expression, [])

    # save only identifier expression
    def _post_identifier(self, expression):
        set_val(expression, [])

    def _post_index_access(self, expression):
        left = get(expression.expression_left)
        right = get(expression.expression_right)
        val = left + right
        set_val(expression, val)

    def _post_literal(self, expression):
        set_val(expression, [])

    def _post_member_access(self, expression):
        expr = get(expression.expression)
        val = expr
        set_val(expression, val)

    def _post_new_array(self, expression):
        set_val(expression, [])

    def _post_new_contract(self, expression):
        set_val(expression, [])

    def _post_new_elementary_type(self, expression):
        set_val(expression, [])

    def _post_tuple_expression(self, expression):
        expressions = [get(e) for e in expression.expressions if e]
        val = [item for sublist in expressions for item in sublist]
        set_val(expression, val)

    def _post_type_conversion(self, expression):
        expr = get(expression.expression)
        val = expr
        set_val(expression, val)

    def _post_unary_operation(self, expression):
        expr = get(expression.expression)
        val = expr
        set_val(expression, val)
