class LCS_weight:
    """
    最长公共子序列：
        通过动态规划，得到矩阵D，
        并从矩阵D中读出一个最长公共子序列
        不支持读出所有的LCS
    """
    def __init__(self):
        self.d = [[]]
        self.matrix = [[]]
        self.res = []
    def init(self, str1, str2, _keyWordsWeight_dict):
        self.keyWordsWeight_dict = _keyWordsWeight_dict
        self.str1 = str1
        self.str2 = str2
        self.len1 = len(str1)
        self.len2 = len(str2)
        self.matrix = [[0 for j in range(self.len2 + 1)] for i in range(self.len1 + 1)]  #j是列数
        self.d = [[0 for j in range(self.len2 + 1)] for i in range(self.len1 + 1)]
    def _get_matrix(self):
        """通过动态规划，构建矩阵"""
        for i in range(1, self.len1+1):
            for j in range(1, self.len2+1):
                if self.str1[i-1] == self.str2[j-1]:
                    if (self.matrix[i-1][j-1] < self.matrix[i-1][j-1] + self.keyWordsWeight_dict[self.str1[i-1]]):
                        self.matrix[i][j] = self.matrix[i-1][j-1] + self.keyWordsWeight_dict[self.str1[i-1]]
                        self.d[i][j] = 0
                    else:
                        self.matrix[i][j] = self.matrix[i - 1][j - 1]
                        self.d[i][j] = -2
                elif self.matrix[i-1][j] >= self.matrix[i][j-1]:
                    self.matrix[i][j] = self.matrix[i-1][j]
                    self.d[i][j] = 1
                else:
                    self.matrix[i][j] = self.matrix[i][j-1]
                    self.d[i][j] = -1
        return self.matrix[self.len1][self.len2]

    def printlcs(self, d, str1, i, j):
        if i == 0 or j == 0:
            return
        if d[i][j] == 0:
            self.printlcs(d, str1, i-1, j-1)
            print(str1[i-1])
            self.res.append(str1[i-1])
        elif d[i][j] == -2:
            self.printlcs(d, str1, i-1, j-1)

        elif d[i][j] == 1:
            self.printlcs(d, str1, i-1, j)
        else:
            self.printlcs(d, str1, i, j-1)
