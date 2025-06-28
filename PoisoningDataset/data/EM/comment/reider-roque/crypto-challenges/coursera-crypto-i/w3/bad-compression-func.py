# Crypto I. Week 3. Constructing Compression Functions. HW assignment from video at 5:00.
# Tested in Python 3

# The collision finding solution:
# E(k1, m1) ^ k1 = E(k2, m2) ^ k2
# E(k1, m1) ^ k1 ^ k2 = E(k2, m2)
# D(k2, (E(k1, m1) ^ k1 ^ k2)) = D(k2, (E(k2, m2)))
# D(k2, (E(k1, m1) ^ k1 ^ k2)) = m2
