# Example of a joint PMF for two coins
import probayes as pb
h0 = pb.RV('c0', prob=0.7)
h1 = pb.RV('c1', prob=0.4)
hh = h0 & h1
HH = hh()
m0 = HH({'c0':True})
m1 = HH({'c1':True})
m2 = HH({'c0':True, 'c1':True})
M0 = HH.marginal('c0')
M1 = HH.marginal('c1')
C0 = HH.conditionalise('c0')
C1 = HH.conditionalise('c1')
print((HH, HH.vals, HH.prob))
print((m0, m0.vals, m0.prob))
print((m1, m1.vals, m1.prob))
print((m2, m2.vals, m2.prob))
print((M0, M0.vals, M0.prob))
print((M1, M1.vals, M1.prob))
print((C0, C0.vals, C0.prob))
print((C1, C1.vals, C1.prob))
