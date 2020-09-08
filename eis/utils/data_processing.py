import matplotlib.pyplot as plt
from altair_saver import save
from dotenv import load_dotenv,find_dotenv
from selenium import webdriver
import os

def flatten_list(a_list):
    return([x for el in a_list for x in el])

#Geographical resolution

def save_fig(name,path,tight=True):
    if tight==True:
        plt.tight_layout()
        
    plt.savefig(f"{path}/{name}")
    
def save_altair(fig,name,w,fig_path,scale=3):
    
    save(fig,f"{fig_path}/{name}.png",method='selenium',webdriver=w,scale_factor=2)

def make_altair_save():
    load_dotenv(find_dotenv())
    w = webdriver.Chrome(os.getenv('chrome_driver_path'))
    return(w)