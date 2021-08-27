# -*- coding: utf-8 -*-
"""
Created on Thu Aug 26 09:41:50 2021

@author: akmal.nordi
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import json

#Start of the app    
st.title('DTSF Project Dashboard')

#Get the name of company
company_input = st.text_input("Please provide your company name")

pwd_input = st.text_input("Please enter your password", type = 'password')
    
#Set up Vendor and Project list
with open('data.json') as json_file:
    project_dict = json.load(json_file)

today = pd.Timestamp.now().normalize()

if company_input == '' or pwd_input == '': #blank input
    pass

elif company_input == 'CIMA' and pwd_input == st.secrets[company_input]['pwd']: #for CIMA
    project_list = list(project_dict.values()) #get all project list
    project_list = [ item for elem in project_list for item in elem] #unpack list of list
    selected_project = st.selectbox('Please select your project', project_list) #user select project
    #read data
    df = pd.read_csv('%s_dim.csv' %(selected_project))
    try:
        df2 = pd.read_csv('%s_fact.csv' %(selected_project))
    except:
        st.write('Project not started yet')
    try:
        df3 = pd.read_csv('%s_last_submit.csv' %(selected_project))
        #change date columns datatype to datetime
        df['start_date'] = pd.to_datetime(df['start_date'])
        df['end_date'] = pd.to_datetime(df['end_date'])
        #calculate the expected progress for each item
        df['exp_progress'] = (today - df['start_date'])/(df['end_date']-df['start_date']) * 100
        #set expected progress to zero if start date not yet start
        df.loc[df.exp_progress < 0, 'exp_progress'] = 0
        avg_exp_progress = df.exp_progress.mean() #average expected progress
        avg_curr_progress = df3.curr_progress.mean() #average current progress
        
        #Create overall progress gauge
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = avg_curr_progress,
            number = { 'suffix' : "%" },
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Overall Progress"},
            gauge = {'axis': {'range': [None, 100]},
                     'bar': {'color': "darkblue"},
                     'steps' : [{'range': [0, 100], 'color': "lightgray"}],
                     'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': avg_exp_progress}}))
    
        st.plotly_chart(fig)
        
        #df4 = df2.groupby(['item_no'])
        #create progress gauge for each item
        for i in range(len(df.iloc[:,0])):
            c1, c2 = st.beta_columns(2)
            with c1:
                st.write("####")
                st.write(df.iloc[i,1])
    
            with c2:
                if df3.iloc[i,1] >50:
                    x_coord = df3.iloc[i,1]-10
                    color_ = 'white'
                else:
                    x_coord = df3.iloc[i,1]+2
                    color_ = 'black'
                target = df.iloc[i,-1]
                fig, ax = plt.subplots()
                fig.set_size_inches(10, 1)
                ax.barh([0], df3.iloc[i,1], align='center', color = 'darkblue')
                ax.plot([target, target], [-0.5,0.5], "red")
                ax.get_yaxis().set_visible(False)
                plt.xlim([0,100])
                ax.annotate('%s%%' %(str(df3.iloc[i,1])), (x_coord,-0.1), size = 20, color = color_)
                ax.set_title('Progress (%)')
                
                st.pyplot(fig)
                
            with st.beta_expander('See remarks'):
                df4 = df2.dropna()
                df4 = df4.loc[df4['item_no'] == i+1]
                date_ = list(df4.iloc[:,-2])
                rem = list(df4.iloc[:,-1])
                for x,y in zip(date_, rem):
                    x = str(x)
                    x = x.split(' ')
                    x = x[0]
                    st.write(x,' - ',y)
                
                
                
    except:
        pass
                

elif pwd_input == st.secrets[company_input]['pwd']: #for Vendor
    project_list = project_dict[company_input] #get project list for selected vendor
    selected_project = st.selectbox('Please select your project', project_list) #user select project
    #read data
    df = pd.read_csv('%s_dim.csv' %(selected_project))
    try:
        df2 = pd.read_csv('%s_fact.csv' %(selected_project))
    except:
        df2 = pd.DataFrame({'item_no':df.iloc[:,0], 'curr_progress':[0]*len(df.iloc[:,0]), 'date':[today]*len(df.iloc[:,0]), 'remarks':['']*len(df.iloc[:,0])})
    try:
        df3 = pd.read_csv('%s_last_submit.csv' %(selected_project))
    except:
        df3 = pd.DataFrame({'item_no':df.iloc[:,0], 'curr_progress':[0]*len(df.iloc[:,0]), 'date':[today]*len(df.iloc[:,0]), 'remarks':['']*len(df.iloc[:,0])})
    #create empty list for progress and remarks
    prog = []
    remarks = []
    
    for i in range(len(df.iloc[:,0])):
        c1, c2 ,c3= st.beta_columns([3,1.5,1.5])
        with c1: #list items
            st.write("##")
            st.write(df.iloc[i,1])

        with c2: #input progress
            last_value = df3.iloc[i,1]
            prog.append(st.number_input("Progress (%)",min_value=0, max_value=100, value=last_value, step=1, key=str(i)))
            
        with c3: #input remarks
            remarks.append(st.text_input('Remarks', key=str((i+1)*10)))
    df3 = pd.DataFrame({'item_no':df.iloc[:,0], 'curr_progress':prog, 'date':[today]*len(df.iloc[:,0]), 'remarks':remarks})
    df2 = df2.append(df3, ignore_index = True)
    

    click_update = st.button('Update')
    if click_update: #user press Update button
        df2.to_csv('%s_fact.csv' %(selected_project), index = False)
        df3.to_csv('%s_last_submit.csv' %(selected_project), index = False)
        st.write('Update successful')
    
    