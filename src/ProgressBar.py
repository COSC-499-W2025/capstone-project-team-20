class Bar:

    #LEGEND:
    #B = byte
    #s = stage
    #b = bar

    STAGES:int  #number of portions in progress bar
    
    #potential lengths for progress bar, will almost always be the max unless you use impossibly small zip files
    POTENTIAL_STAGES = [64,32,16,8,4,2,1]

    TOTALB:int  #total amount of bytes
    total:int   #current amount of bytes
    STAGEB:int  #how many bytes in a substage
    sDone:int   #stages completed
    sLeft:int   #stages remaining
    sSub:int    #from 0 to 7, how far through the sub-stage are you 
    sB:int      #amount of bytes in current stage

    bDone:str   #string representing completed portion
    BSUB = []   #in between stages
    bLeft:str   #string representing remaining portion

    def __init__(self, totalbytes:int):
        self.TOTALB = totalbytes
        self.total = 0
        self.sDone = 0

        #if checks for a valid totalbytes fail, abort is set to True, if True, bar will be really short and already completed to avoid error
        abort = False

        #logic for adjusting stage count and stage size so that STAGES is never 0 and the progress bar still runs smoothly:
        idx = 0
        self.STAGEB = int(totalbytes/8) #8 portions per bar, so needs to be at least 8 bytes to function

        if self.STAGEB <= 0: # if self.STAGEB is already 0 at this point, make the progress bar already complete
            abort = True
            self.STAGES = 1
            self.STAGEB = 1
        else:
            while (int(self.STAGEB/self.POTENTIAL_STAGES[idx])<=0): #if there are too many stages for the totalbytes, lessen the amount of stages
                idx+=1
                if idx > len(self.POTENTIAL_STAGES) -1:
                    abort = True
                    idx = len(self.POTENTIAL_STAGES) -1
                    break
            self.STAGEB = int(self.STAGEB/self.POTENTIAL_STAGES[idx])
            self.STAGES = self.POTENTIAL_STAGES[idx]
        

        self.sLeft = self.STAGES
        self.sB = 0
        self.sSub = 0
        self.BSUB = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉",""]
        
        self.bDone = ''
        self.bLeft = ''
        count=1
        while count<self.STAGES:
            self.bLeft += ' '
            count+=1

        if abort:
            self.bDone = '█'
            self.bLeft = ''
            self.sDone = 1
            self.sLeft = 0
            self.total = self.TOTALB
            self.sSub = 8
        
        print('|' + self.bDone + self.BSUB[self.sSub] + self.bLeft + '|' + ' (' + str(self.total) + ' Bytes/' + str(self.TOTALB) + ' Bytes)\r',end="")
    
    def stageup(self):
        '''increase the stage by one'''
        
        if (self.sDone <= self.STAGES):
            self.sSub += 1 #increase sSub
            if self.sSub >= 8:
                self.bLeft = self.bLeft[:-1] #remove incomplete portion from the bar
                self.sDone+=1 #increase completed stages by one
                self.sLeft-=1 #reduce remaining stages by one
                if (len(self.bDone)<self.STAGES):
                    self.bDone += '█'
                self.sSub =0
        
        if self.total>=self.TOTALB or self.sDone >= self.STAGES:
            self.total = self.TOTALB
            self.sSub = 8 #empty character so that the bar still looks full
        
    def update(self, sizeB:int):
        '''takes the size of the file just analyzed and updates the progress bar'''

        # add the analyzed bytes to current stage:
        if sizeB>0:
            self.sB += sizeB
            self.total += sizeB #add the size of stage to running total

        #finishes progress bar if it is complete but not at the right total
        if self.total >= self.STAGEB*8*self.STAGES or self.total >= self.TOTALB:
            self.total = self.TOTALB
            self.sSub = 8
            self.sB = 0
            while (len(self.bDone) < self.STAGES):
                self.bDone += '█'

        # check if stage(s) completed:
        if (self.sB >= self.STAGEB):
            while (self.sB >= self.STAGEB): #while amount progressed > bytes per stage:
                #subtract bytes per stage from new bytes analyzed
                self.sB -= self.STAGEB

                #increase stage:
                self.stageup()

                #print:
                #(\r returns cursor to the start of the line, end="" prevents newline, so essentially the string will keep replacing itself)
                print('|' + self.bDone + self.BSUB[self.sSub] + self.bLeft + '|' + ' (' + str(self.total) + ' Bytes/' + str(self.TOTALB) + ' Bytes)\r',end="")
                #time.sleep(0.0001)
        else:
            print('|' + self.bDone + self.BSUB[self.sSub] + self.bLeft + '|' + ' (' + str(self.total) + ' Bytes/' + str(self.TOTALB) + ' Bytes)\r',end="")