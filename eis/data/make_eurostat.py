import eurostat
import eis
import yaml
import ratelim
import time
from eis.utils.data_processing import flatten_list
import logging
import os

project_dir = eis.project_dir 

target_dir = f'{project_dir}/data/raw/eurostat'

def make_eurostat_table(code,toc_df,path=target_dir):
    '''

    This function extracts and saves a eurostat table with a readable name together with 
    a yaml with its data dictionary
    
    Args:
        code (str) is the code for the table
        toc_df (df) is a dataframe with a table of contents (we use it to create the schema)
        path (str) is the destination for storing data and schema
    
    '''
    try:
        table = eurostat.get_data_df(code)
    
        if 'time\geo' in table.columns:

            struct_name = 'time\geo'
            melt_var_name = 'geo'

            meta_cols = [x for x in table.columns if ((len(x)>2)&(not any(name in x for name in 
                                                                      ['EU','EA'])))]

        else:
            struct_name = 'geo\\time'
            melt_var_name = 'time'

            meta_cols = [x for x in table.columns if type(x)!=int]

        table_long = table.melt(id_vars=meta_cols,
                                    var_name=melt_var_name,
                                    value_name=code)

        #Create schema

        sch= make_schema(table_long,code,toc_df,struct_name,melt_var_name)

        #Save table and schema
        table_long.to_csv(f'{path}/{code}.csv',index=False)

        with open(f'{path}/{code}.yaml','w') as outfile:
            yaml.dump(sch,outfile)
            
    except:
        #A small number of eurostat tables don't work with this package.
        print('   API failure')


def make_schema(table,code,toc_df,struct_name,melt_var_name):
    '''
    Creates a schema for a table. The schema contains some basic information about
    the table from the toc df and the data dict for all relevant columns.
    
    Args:
        table (df) is the table we want to create the schema for
        code (str) is the code for the table (we use to get the metadata)
        toc_df (df) is the table of contents df where we get some metadata from
        struct_name (str) is the name of a variable telling us whether the columns have 
            years or countries
        melt_var_name (str) is the name of the variable that we have melted (could be country
            or year)
        
    '''
    
    #Create schema
    
    sch = {}
    
    sch['schema'] = {}
    
    #Add metadata from table of contents
    metadata = toc_df.loc[toc_df['code']==code].to_dict()
    
    for k,v in metadata.items():
        
        sch[k] = v
    
    #Add category codes from df columns
    for col in table.columns:
        
        if col not in [code,struct_name,melt_var_name]:
            
            #The dict considers all potential values for a variable. We focus on those
            #that are actually present
            potential_values = eurostat.get_dic(col)
            
            actual_values = set(potential_values.keys()) & set(table[col])        
            actual_dict = {k:v for k,v in potential_values.items() if k in actual_values}
            
            sch['schema'][col] = actual_dict
            
        sch['schema'][melt_var_name] = list(set(table[melt_var_name]))
        
        sch['schema'][struct_name.split('\\')[0]] = list(set(table[struct_name]))
        
    return(sch)
    
def collect_data_for_topic(toc_df,keywords,target_path,delay=0.5):
    '''
    Collects data for a topic (based on whether a keyword appears on it)
    
    Args:
        toc_df (df) is the table of contents df
        keywords (list) is a list of keywords to query 
        delay (float) is the second delay in queries that we introduce
        target ()
    
    '''
    codes = []
    
    for k in keywords:
        
        data_codes = [x['code'] 
                     for rid,x in eurostat.subset_toc_df(
                         toc_df,k).iterrows() if x['type']=='dataset']
        codes.append(data_codes)
    
    codes_flat = set(flatten_list(codes))
    
    print(codes_flat)
    
    for c in codes_flat:
        
        time.sleep(delay)
        
        logging.info(f'Making {c}')
        
        make_eurostat_table(c,toc_df,target_path)
 
########   
#Collect data
########

with open(f"{project_dir}/model_config.yaml",'r') as infile:
    table_codes = yaml.load(infile)['eurostat_inventory']

print(table_codes)

toc_df = eurostat.get_toc_df()

#For the table codes we collect the data
if os.path.exists(f"{target_dir}/selected_tables")==False:
    os.mkdir(f"{target_dir}/selected_tables")

for c in table_codes:
    make_eurostat_table(c,toc_df,f"{target_dir}/selected_tables")

#For each of these topics collect the data and save in its own special directory
for topic in ['skills','innovation','digital','education']:

    if os.path.exists(f"{target_dir}/{topic}")==False:
        os.mkdir(f"{target_dir}/{topic}")

    target_2 = f"{target_dir}/{topic}"
    collect_data_for_topic(toc_df,[topic],target_2)

