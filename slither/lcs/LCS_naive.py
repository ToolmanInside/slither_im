class LCS_naive:
    """
    最长公共子序列：
        通过动态规划，得到矩阵D，
        并从矩阵D中读出一个最长公共子序列
        不支持读出所有的LCS
    """

    def __init__(self):
        self.matrix = [[]]

    def init(self, str1, str2):
        self.str1 = str1
        self.str2 = str2
        self.len1 = len(str1)
        self.len2 = len(str2)
        self.matrix = [[0 for i in range(self.len2 + 1)] for j in range(self.len1 + 1)]

    def _get_matrix(self):
        """通过动态规划，构建矩阵"""
        for i in range(self.len1):
            for j in range(self.len2):
                if self.str1[i] == self.str2[j]:
                    self.matrix[i + 1][j + 1] = self.matrix[i][j] + 1
                else:
                    self.matrix[i + 1][j + 1] = max(self.matrix[i][j + 1], self.matrix[i + 1][j])

    def _matrix_show(self, matrix):
        """展示通过动态规划所构建的矩阵"""
        print("----matrix-----")
        print(" ", " ", end=" ")
        for ch in self.str2:
            print(ch, end=" ")
        print()
        for i in range(len(matrix)):
            if i > 0:
                print(self.str1[i - 1], end=" ")
            else:
                print(" ", end=" ")
            for j in range(len(matrix[i])):
                print(matrix[i][j], end=" ")
            print()
        print("---------------")

    def _get_one_lcs_from_matrix(self):
        i = len(self.matrix) - 1
        if i == 0:
            print("matrix is too small")
            return
        j = len(self.matrix[0]) - 1
        res = []
        while not (i == 0 or j == 0):
            if self.str1[i - 1] == self.str2[j - 1]:
                res.append(self.str1[i - 1])
                i -= 1
                j -= 1
            else:
                if self.matrix[i - 1][j] > self.matrix[i][j - 1]:
                    i = i - 1
                else:
                    j = j - 1
        return res[::-1]

    def get_lcs(self):
        self._get_matrix()
        # self._matrix_show(self.matrix)
        lcsList = self._get_one_lcs_from_matrix()
        # print (lcs)
        return lcsList

class LCS(LCS_naive):
    """
    继承自LCS_naive
    增加获取所有LCS的支持
    """

    def __init__(self):
        LCS_naive.__init__(self)

    def _get_all_lcs_from_matrix(self):
        lcsList = self._pre_travesal(self.len1, self.len2, [])
        return  lcsList

    def _pre_travesal(self, i, j, lcs_ted):
        if i == 0 or j == 0:
            #print("".join(lcs_ted[::-1]))
            return lcs_ted[::-1]
        if self.str1[i - 1] == self.str2[j - 1]:
            lcs_ted.append(self.str1[i - 1])
            self._pre_travesal(i - 1, j - 1, lcs_ted)
        else:
            if self.matrix[i - 1][j] > self.matrix[i][j - 1]:
                self._pre_travesal(i - 1, j, lcs_ted)
            elif self.matrix[i - 1][j] < self.matrix[i][j - 1]:
                self._pre_travesal(i, j - 1, lcs_ted)
            else:
                ###### 分支
                self._pre_travesal(i - 1, j, lcs_ted[:])
                self._pre_travesal(i, j - 1, lcs_ted)

    def get_lcs(self):
        self._get_matrix()
        #self._matrix_show(self.matrix)
        self._get_all_lcs_from_matrix()