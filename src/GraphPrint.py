import sys
import time

def fillprint(fillstring:str, size:int, fillchar:str):

    '''prints with set size, right justified (cleans up the code somewhat by reducing temporary variables)'''

    #error checking
    if (len(fillchar)!=1):
        return -1
    if (size <=0):
        return -1

    sys.stdout.write(f"{str(fillstring):{fillchar}>{size}}")


def graph(title:str, list_of_name_value_pairs:list, value_units:str): 

    '''Prints a graph of the values'''

    #-----example input: graph('Programming language', [['Python', 1830],['Java', 6904]], "lines")-----#

    size = 64  #this is the maximum size

    num_pairs = len(list_of_name_value_pairs)

    cycle = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉","█"]
    total = 0

    indent = 0

    #calculate total
    for pair in list_of_name_value_pairs:
        #error checking
        if not (isinstance(pair, list)):
            return -1
        if not (len(pair)==2):
            return -1
        if not (isinstance(pair[0], str)):
            return -1
        if not (isinstance(pair[1], int)):
            return -1
        #calculate total
        total = total + pair[1]
        #calculate indent amount
        while (len(pair[0])+3)>indent:
            indent+=1

    maximum = 0
    
    #calculate percent and size of bar
    for pair in list_of_name_value_pairs:
        pair.append(int((pair[1]/total)*size))
        pair.append((pair[1]/total))
        if pair[2]>maximum:
            maximum=pair[2]+1
        pair.append((int(((pair[1]/total)*size)*8))%8)
        pair.append(0)
        pair.append(pair[2])
        pair.append(0)
    
    segment_value = total/size
    
    #pair[0] = name
    #pair[1] = value
    #pair[2] = length of bar
    #pair[3] = percent
    #pair[4] = cycle
    #pair[5] = full segment count
    #pair[6] = bar remaining
    #pair[7] = running total

    top = '╔════════════════════════════════════════════════════════════════'
    mid = '║                                                                '
    bot = '╚════════════════════════════════════════════════════════════════'

    l_end = '╢'
    r_end = ''

    fillprint('',indent+64,'─')
    sys.stdout.write('\n'+title +':\n')
    i=0
    while (i<maximum):
        #top border
        fillprint('',indent, ' ')
        sys.stdout.write(top+'\n')
        fillprint('',indent, ' ')
        sys.stdout.write(mid+'\n')


        for pair in list_of_name_value_pairs:

            fillprint("["+pair[0]+"]─",indent, ' ')
            sys.stdout.write(l_end)

            if pair[6]>0: #only increase cycle and running total if remaining bar is not 0
                pair[7] += segment_value
                pair[5]+=1
            else:
                pair[7]=pair[1]
            
            if pair[5]>0:
                fillprint('',pair[5],'█') # prints filled portion
            
            if pair[6]<=0:
                sys.stdout.write(cycle[pair[4]]) #prints the last remaining portion when bar is complete
            
            sys.stdout.write(r_end)
            sys.stdout.write('─('+str(int(pair[7]))+' '+value_units+')\n')
            
            #print a separating line below
            fillprint('',indent,' ')
            sys.stdout.write(mid+'\n')

            if pair[6]>0:
                pair[6]-=1

        #bottom border
        fillprint('',indent, ' ')
        sys.stdout.write(bot+'\n')

        sys.stdout.write('Of your '+value_units+' contributed:\n')
        for pair in list_of_name_value_pairs:
            sys.stdout.write('    ‣')
            sys.stdout.write(f"{pair[7]/total:.2%}")
            sys.stdout.write(" were ")
            sys.stdout.write(pair[0])
            sys.stdout.write("\n")
        fillprint('',indent+64,'─')
        sys.stdout.write("\n")

        #terminal pointer up
        for g in range((num_pairs*2)+num_pairs+5):
            sys.stdout.write("\033[A")


        time.sleep(0.01)
        i+=1
    
    
    for g in range((num_pairs*2)+num_pairs+5):
        sys.stdout.write("\n")

#Use this to test:

vals = [['Python', 1830],['Java', 6904]]
graph('Programming language', vals, "lines")

