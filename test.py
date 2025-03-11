import matplotlib.pyplot as plt
import numpy as np
 
df = { 'TEAM-1': [-0.3, -0.5, 0.5, 0.3, -0.8, 0.1],
       'TEAM-4': [0.1, 0.2, -0.2, -0.4, 0.4, 0.8],
       'TEAM-6': [0.3, 0.5, -0.4, -0.6, 0.6, 1.2]}
 
mineraller = ["Anhidrit", "Jips", "Kalsedon", "Kuvars", "Dolomit", "Kalsit"]
for idx, mineral in enumerate(mineraller):
    plt.plot(df.keys(), [v[idx] for v in df.values()], marker='o', label=mineral)
 
plt.axhline(y=0, color='k', linestyle='--')
plt.xlabel("Kuyular")
plt.ylabel("Doygunluk İndeksi (SI)")
plt.legend()
plt.show()