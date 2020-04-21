import matplotlib.pyplot as plt

def flatten_list(a_list):
    return([x for el in a_list for x in el])

#Geographical resolution

def save_fig(name,path,tight=True):
    if tight==True:
        plt.tight_layout()
        
    plt.savefig(f"{path}/{name}")
    