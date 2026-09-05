from datetime import datetime


def find_free_slots(schedules: list, start_time: datetime, end_time: datetime) -> list:
   
   
   busy = []
   for s in schedules:
       s0 = max(start_time, s["start"])  
       s1 = min(end_time, s["end"])
       if s0 < s1:                       
           busy.append((s0, s1))

   
   if not busy:
       return [(start_time, end_time)]

   
   busy.sort()
   merged = [busy[0]]
   for cur_start, cur_end in busy[1:]:
       last_start, last_end = merged[-1]
       if cur_start <= last_end:         
           merged[-1] = (last_start, max(last_end, cur_end))
       else:
           merged.append((cur_start, cur_end))

   
   free = []
   if merged[0][0] > start_time:         
       free.append((start_time, merged[0][0]))
   for i in range(len(merged) - 1):      
       free.append((merged[i][1], merged[i + 1][0]))
   if merged[-1][1] < end_time:          
       free.append((merged[-1][1], end_time))

   return free