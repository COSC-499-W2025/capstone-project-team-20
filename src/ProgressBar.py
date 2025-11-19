class Bar:

    STAGES:int  #number of portions in progress bar
    
    #potential lengths for progress bar, will almost always be the max unless you use impossibly small zip files
    POTENTIAL_STAGES = [64,32,16,8,4,2,1]

    TOTAL_BYTES:int  #current_total amount of bytes
    current_total:int   #current amount of bytes
    STAGE_SIZE:int  #how many bytes in a substage
    stages_completed:int   #stages completed
    stages_remaining:int   #stages remaining
    sub_stage_idx:int    #from 0 to 7, how far through the sub-stage are you 
    stage_progress:int      #amount of bytes in current stage
    
    TOTAL_digits:int

    bar_complete:str   #string representing completed portion
    SUB_CHARS = []   #in between stages will go here
    bar_remaining:str   #string representing remaining portion

    def __init__(self, TOTAL_BYTES:int):
        self.TOTAL_BYTES = TOTAL_BYTES
        self.TOTAL_digits = len(str(TOTAL_BYTES))
        self.current_total = 0
        self.stages_completed = 0

        #if checks for a valid TOTAL_BYTES fail, abort is set to True, if True, bar will be really short and already completed to avoid error
        abort = False

        #logic for adjusting stage count and stage size so that STAGES is never 0 and the progress bar still runs smoothly:
        idx = 0
        self.STAGE_SIZE = int(TOTAL_BYTES/8) #8 portions per bar, so needs to be at least 8 bytes to function

        if self.STAGE_SIZE <= 0: # if self.STAGE_SIZE is already 0 at this point, make the progress bar already complete
            abort = True
            self.STAGES = 1
            self.STAGE_SIZE = 1
        else:
            while (int(self.STAGE_SIZE/self.POTENTIAL_STAGES[idx])<=0): #if there are too many stages for the TOTAL_BYTES, lessen the amount of stages
                idx+=1
                if idx > len(self.POTENTIAL_STAGES) -1:
                    abort = True
                    idx = len(self.POTENTIAL_STAGES) -1
                    break
            self.STAGE_SIZE = int(self.STAGE_SIZE/self.POTENTIAL_STAGES[idx])
            self.STAGES = self.POTENTIAL_STAGES[idx]
        

        self.stages_remaining = self.STAGES
        self.stage_progress = 0
        self.sub_stage_idx = 0
        self.SUB_CHARS = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉",""]
        
        self.bar_complete = ''
        self.bar_remaining = ''
        count=1
        while count<self.STAGES:
            self.bar_remaining += ' '
            count+=1

        if abort:
            self.bar_complete = '█'
            self.bar_remaining = ''
            self.stages_completed = 1
            self.stages_remaining = 0
            self.current_total = self.TOTAL_BYTES
            self.sub_stage_idx = 8
        
        print('|' + self.bar_complete + self.SUB_CHARS[self.sub_stage_idx] + self.bar_remaining + '|' + ' (' + f'{self.current_total:0{self.TOTAL_digits}d}' + ' Bytes/' + str(self.TOTAL_BYTES) + ' Bytes)\r',end="")
    
    def stageup(self):
        '''increase the stage by one'''
        
        if (self.stages_completed <= self.STAGES):
            self.sub_stage_idx += 1 #increase sub_stage_idx
            if self.sub_stage_idx >= 8:
                self.bar_remaining = self.bar_remaining[:-1] #remove incomplete portion from the bar
                self.stages_completed+=1 #increase completed stages by one
                self.stages_remaining-=1 #reduce remaining stages by one
                if (len(self.bar_complete)<self.STAGES):
                    self.bar_complete += '█'
                self.sub_stage_idx =0
        
        if self.current_total>=self.TOTAL_BYTES or self.stages_completed >= self.STAGES:
            self.current_total = self.TOTAL_BYTES
            self.sub_stage_idx = 8 #empty character so that the bar still looks full
        
    def update(self, sizeB:int):
        '''takes the size of the file just analyzed and updates the progress bar'''

        # add the analyzed bytes to current stage:
        if sizeB>0:
            self.stage_progress += sizeB
            self.current_total += sizeB #add the size of stage to running current_total

        #finishes progress bar if it is complete but not at the right current_total
        if self.current_total >= self.STAGE_SIZE*8*self.STAGES or self.current_total >= self.TOTAL_BYTES:
            self.current_total = self.TOTAL_BYTES
            self.sub_stage_idx = 8
            self.stage_progress = 0
            while (len(self.bar_complete) < self.STAGES):
                self.bar_complete += '█'

        # check if stage(s) completed:
        if (self.stage_progress >= self.STAGE_SIZE):
            while (self.stage_progress >= self.STAGE_SIZE): #while amount progressed > bytes per stage:
                #subtract bytes per stage from new bytes analyzed
                self.stage_progress -= self.STAGE_SIZE

                #increase stage:
                self.stageup()

                #print:
                #(\r returns cursor to the start of the line, end="" prevents newline, so essentially the string will keep replacing itself)
                print('|' + self.bar_complete + self.SUB_CHARS[self.sub_stage_idx] + self.bar_remaining + '|' + ' (' + f'{self.current_total:0{self.TOTAL_digits}d}' + ' Bytes/' + str(self.TOTAL_BYTES) + ' Bytes)\r',end="")
                #time.sleep(0.0001)
        else:
            print('|' + self.bar_complete + self.SUB_CHARS[self.sub_stage_idx] + self.bar_remaining + '|' + ' (' + f'{self.current_total:0{self.TOTAL_digits}d}' + ' Bytes/' + str(self.TOTAL_BYTES) + ' Bytes)\r', end='')