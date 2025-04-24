#Example script

import time
import PyGPU as gpu

# Initialize the PDH query
query = gpu.init_gpu_state()
instances = gpu.setup_gpu_instances()

# For engine specific usage, e.g., "engtype_3D"
query, handles = gpu.setup_gpu_query_from_instances(query, instances, "engtype_3D") 
GPU_usage, target_luid = gpu.get_gpu_usage(query, handles) # Can be used to get LUID with highest usage; Can also take a specific LUID as a third input

print("All unique LUIDs:")
for luid in handles:
    print(luid)

print(f"Current Top LUID: {target_luid}, 3D engine usage: {GPU_usage}%")

#For all engine types, e.g., "engtype_", leave it empty
query, handles = gpu.setup_gpu_query_from_instances(query, instances)

print("For sum of all GPU engines for a specific LUID:")

# Add target LUID to the query for a specific LUID 
# Periodic sampling (e.g., every second)
while True:
    usage, top_luid = gpu.get_gpu_usage(query, handles, target_luid)
    print(f"Total GPU Engine Utilization: {usage}%, LUID: {top_luid}")
    time.sleep(0.9)  # Update every second; 0.1s already used within the get_gpu_usage function