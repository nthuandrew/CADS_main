# 判決結果分類_轉換成doc2vec向量
# 讀取標注資料
import pandas as pd
import numpy as np
from collections import Counter
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
from importlib import import_module, reload
fp = reload(import_module('dataset.custody-prediction-dataset.custody-prediction-data-preparation.lib.filepath_process'))
get_path_from_json = fp.get_path_from_json

path = get_path_from_json('for_classifier_training/judgment_result_seg_train', 'msg')
df_train = pd.read_msgpack(path)
# df_train = pd.read_msgpack('/Users/juanmurphy/Documents/ENV/custody-prediction-modeling-murphy/dataset/for_classifier_training/judgment_result_seg_train(624).msg')

path = get_path_from_json('for_classifier_training/judgment_result_seg_test', 'msg')
df_test = pd.read_msgpack(path)
# df_test = pd.read_msgpack('/Users/juanmurphy/Documents/ENV/custody-prediction-modeling-murphy/dataset/for_classifier_training/judgment_result_seg_test(156).msg')

path = get_path_from_json('for_classifier_training/judgment_result_seg_train_neu', 'msg')
df_train_neu = pd.read_msgpack(path)

path = get_path_from_json('for_classifier_training/judgment_result_seg_test_neu', 'msg')
df_test_neu = pd.read_msgpack(path)

df_train, df_val = train_test_split(df_train, test_size=0.2, random_state=None)
df_train_neu, df_val_neu = train_test_split(df_train_neu, test_size=0.2, random_state=None)

# 將 neutral 與 非neutral 分開
import matplotlib

categorical = ['Result','Willingness','AK','RK','AN','RN', 'Type']
meta_info = ['filename', 'ID', 'Others']
# column_prefixes = ['AA', 'RA', 'AD', 'RD', 'neutral']

df_list = [df_train, df_val, df_test]
df_list_neu = [df_train_neu, df_val_neu, df_test_neu]


for df, df_neu in zip(df_list, df_list_neu):
    all_neutral_columns = df_neu.columns[df_neu.columns.to_series().str.contains('neutral')].tolist()

    non_neutral_columns = sorted(list(set(list(matplotlib.cbook.flatten(df.columns.tolist()))) - set(all_neutral_columns) - set(categorical) - set(meta_info)))

# ## 讀取模型
from gensim.models.doc2vec import Doc2Vec

model_dbow = Doc2Vec.load('models/Doc2Vec_有利不利/dbow_100_ADV_DIS_model.bin')

model_dmm = Doc2Vec.load('models/Doc2Vec_有利不利/dmm_100_ADV_DIS_model.bin')

# ### 並聯模型

from gensim.test.test_doc2vec import ConcatenatedDoc2Vec
model_dbow.random.seed(1234)
model_dmm.random.seed(1234)
concate_model = ConcatenatedDoc2Vec([model_dbow, model_dmm])
seed_funcs = [model_dbow.random.seed, model_dmm.random.seed]

# ## 文字標記轉成 Doc2Vec 向量

import numpy as np

def seg_to_DocVec(input_txt, model, seed_funcs=seed_funcs):
#     # Doc2Vec infer_vector() could (as option?) offer deterministic result · Issue #447 · RaRe-Technologies/gensim
#     # https://github.com/RaRe-Technologies/gensim/issues/447
#     for seed_func in seed_funcs:
#         seed_func(0)
    avgDoc2Vec = []
    for _ in range(1):
        avgDoc2Vec.append(np.array(model.infer_vector(input_txt)))
        
    avgDoc2Vec = np.mean(avgDoc2Vec, axis=0)
    
    return avgDoc2Vec

def get_random_item(dataframe, selected_columns, row_index , verbose=False):
#     random_index = np.random.randint(len(selected_columns))
    random_index = len(selected_columns) - 1
    #print(random_index)
    random_column = selected_columns[random_index]
    #print(random_column)
    if verbose:
        print('row index: %d, random column: %s' % (row_index, random_column))
        #print(dataframe[random_column].loc[row_index])
    return dataframe[random_column].loc[row_index]

# set True for debug
debug = False

# ### 轉成doc2vec

import copy
from itertools import count
from collections import defaultdict 
#df2 = pd.DataFrame(columns=non_neutral_columns+all_neutral_columns)

from importlib import import_module, reload
fp = reload(import_module('dataset.custody-prediction-dataset.custody-prediction-data-preparation.lib.filepath_process'))
save_path_to_json = fp.save_path_to_json


mapping_dict = {0:'train', 1:'val', 2:'test'}

max_multiple = 20

df_list3 = []
# 先處理 neutral columns
for index, df in zip(count(), df_list):
    
    if index == 0:
        # training set
        multiple_times = max_multiple
    else:
        # validate & test set
        multiple_times = 1
        
    #df_list3[index] = pd.concat([df_list3[index]]*multiple_times, ignore_index=True)
    
    tmp_df = pd.DataFrame(columns=df.columns)
    model_dbow.random.seed(1234)
    model_dmm.random.seed(1234)
    concate_model = ConcatenatedDoc2Vec([model_dbow, model_dmm])
    for multiple_time in range(multiple_times):
#         model_dbow.random.seed(0)
#         model_dmm.random.seed(0)
#         concate_model = ConcatenatedDoc2Vec([model_dbow, model_dmm])
        tmp_df2 = pd.DataFrame(columns=df.columns)
        tmp_df2[categorical+meta_info] = df[categorical+meta_info]
        # display(tmp_df2)
        for i_column in non_neutral_columns:
            # select none empty entries, and apply txt_to_clean, clean_to_seg, seg_to_DocVec
            if debug:
                tmp_df2[i_column] = df[i_column].apply(lambda x: i_column)
            else:
                #df2[i_column] = df[i_column].apply(lambda x: np.zeros(200))
                tmp_df2[i_column] = df.loc[~df.loc[:,i_column].isnull()][i_column].apply(seg_to_DocVec, model=concate_model)
        # display(tmp_df2)
        tmp_df = pd.concat([tmp_df, tmp_df2], ignore_index=True)
        #temp_df2_list_dict[index].append(tmp_df2)
        
    # save training se
    total_number = len(tmp_df)
    if mapping_dict[index] != 'train':
        path = save_path_to_json('dataset/for_classifier_training/judgment_result_doc2vec_{}'.format(mapping_dict[index]), 'msg', str(total_number))
        tmp_df.to_msgpack(path)
    else:
        path = save_path_to_json('dataset/for_classifier_training/judgment_result_doc2vec_{}'.format(mapping_dict[index]), 'msg', 'murphy')
        tmp_df.to_msgpack(path)
    df_list3.append(tmp_df)

import copy
from itertools import count
from collections import defaultdict 
#df2 = pd.DataFrame(columns=non_neutral_columns+all_neutral_columns)

from importlib import import_module, reload
fp = reload(import_module('dataset.custody-prediction-dataset.custody-prediction-data-preparation.lib.filepath_process'))
save_path_to_json = fp.save_path_to_json


mapping_dict = {0:'train_neu', 1:'val_neu', 2:'test_neu'}

max_multiple = 20

df_list3_neu = []
# df_list3 = pd.concat([df_list3]*max_multiple, ignore_index=True)

# temp_df2_list_dict = defaultdict(list)

# 先處理 neutral columns
for index, df in zip(count(), df_list_neu):
    
    if index == 0:
        # training set
        multiple_times = max_multiple
    else:
        # validate & test set
        multiple_times = 1
        
    #df_list3[index] = pd.concat([df_list3[index]]*multiple_times, ignore_index=True)
    
    tmp_df = pd.DataFrame(columns=df.columns)
    model_dbow.random.seed(0)
    model_dmm.random.seed(0)
    concate_model = ConcatenatedDoc2Vec([model_dbow, model_dmm])
    for multiple_time in range(multiple_times):
        tmp_df2 = pd.DataFrame(columns=df.columns)
        tmp_df2['ID'] = df['ID']
        # display(tmp_df2)
        for i_column in all_neutral_columns:
            # select none empty entries, and apply txt_to_clean, clean_to_seg, seg_to_DocVec
            if debug:
                tmp_df2[i_column] = df[i_column].apply(lambda x: i_column)
            else:
                #df2[i_column] = df[i_column].apply(lambda x: np.zeros(200))
                tmp_df2[i_column] = df.loc[~df.loc[:,i_column].isnull()][i_column].apply(seg_to_DocVec, model=concate_model)
        # display(tmp_df2)
        tmp_df = pd.concat([tmp_df, tmp_df2], ignore_index=True)
        #temp_df2_list_dict[index].append(tmp_df2)
        
    # save training set
    total_number = len(tmp_df)
    path = save_path_to_json('dataset/for_classifier_training/judgment_result_doc2vec_{}'.format(mapping_dict[index]), 'msg', str(total_number))
    tmp_df.to_msgpack(path)

            
    #df_list3[index] = pd.concat(temp_df2_list_dict[index], ignore_index=True)
    df_list3_neu.append(tmp_df)




