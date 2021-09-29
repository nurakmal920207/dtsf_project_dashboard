# -*- coding: utf-8 -*-
"""
This app is created as an interface to enable vendor to update the progress of DTSF project
and for CIMA personnel to get fast update on the progress through the dashboard
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import json
import yagmail
from PIL import Image
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

#Start of the app
c1, c2, c3 = st.beta_columns([1,4,1])
with c1:
    image = Image.open('Final Logo DTSF.png')
    st.image(image)

with c2:
    st.title('DTSF PROJECT PROGRE')

with c3:
    image = Image.open('CIMA Logo.png')
    st.image(image)

#Get the name of company
with st.form(key='my_form'):
    company_input = st.text_input("Please provide your company name")
    pwd_input = st.text_input("Please enter your password", type = 'password')
    submit_button = st.form_submit_button(label='Submit')

try:
    if pwd_input != st.secrets[company_input]['pwd'] and pwd_input != '':
        st.write('Wrong Password')
except:
    if pwd_input != '':
        st.write('Wrong company name')
        pwd_input = ''

#Set up Vendor and Project list
with open('vendor_data.json') as json_file:
    project_dict = json.load(json_file)

today = pd.Timestamp.now().normalize()

# Create a connection object.
cr_list = ['type',
            'project_id',
            'private_key_id',
            'private_key',
            'client_email',
            'client_id',
            'auth_uri',
            'token_uri',
            'auth_provider_x509_cert_url',
            'client_x509_cert_url']

credentials = { x : st.secrets['cred'][x] for x in cr_list}
gc = gspread.service_account_from_dict(credentials)

if company_input == '' or pwd_input == '': #blank input
    pass

elif company_input == 'CIMA' and pwd_input == st.secrets[company_input]['pwd']: #for CIMA
    project_list = list(project_dict.values()) #get all project list
    project_list = [ item for elem in project_list for item in elem] #unpack list of list
    selected_project = st.selectbox('Please select your project', project_list) #user select project
    #read data
    sh = gc.open(selected_project)
    df = get_as_dataframe(sh.worksheet('dimension'))
    df.dropna(axis=1, how='all', inplace=True)
    df.dropna(how='all', inplace=True)
    try:
        df2 = get_as_dataframe(sh.worksheet('fact'))
        df2.dropna(axis=1, how='all', inplace=True)
        df2.dropna(how='all', inplace=True)
    except:
        st.write('Project not yet started')
    try:
        df3 = get_as_dataframe(sh.worksheet('last_submit'))
        df3.dropna(axis=1, how='all', inplace=True)
        df3.dropna(how='all', inplace=True)
        #change date columns datatype to datetime
        df['start_date'] = pd.to_datetime(df['start_date'])
        df['end_date'] = pd.to_datetime(df['end_date'])
        #calculate the expected progress for each item
        df['exp_progress'] = (today - df['start_date'])/(df['end_date']-df['start_date']) * 100
        #set expected progress to zero if start date not yet start
        df.loc[df.exp_progress < 0, 'exp_progress'] = 0
        
        df['weighted_exp_progress'] = df.exp_progress * df.weightage
        avg_exp_progress = df.weighted_exp_progress.sum() #average expected progress
        
        df3['weighted_curr_progress'] = df3.curr_progress * df.weightage
        avg_curr_progress = df3.weighted_curr_progress.sum() #average current progress
        
        df3['actual_day'] = df3.curr_progress * (df.end_date - df.start_date) / 100
        df3['expected_day'] = df.exp_progress * (df.end_date - df.start_date) / 100
        df3['days'] = df3.actual_day - df3.expected_day #calculate how many days ahead or late
        df3['weighted_days'] = df3.days * df.weightage
        mean_weighted_days = df3.weighted_days.sum().days
        if mean_weighted_days < 0:
            text = 'Overall Progress - %s days late' %(mean_weighted_days*-1)
            color = "red"
        elif mean_weighted_days > 0:
            text = 'Overall Progress - %s days ahead' %(mean_weighted_days)
            color = "green"
        else:
            text = 'Overall Progress - On time'
            color = 'black'

        #Create overall progress gauge
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = avg_curr_progress,
            number = { 'suffix' : "%" },
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': text},
            gauge = {'axis': {'range': [None, 100]},
                     'bar': {'color': "#146C9C"},
                     'steps' : [{'range': [0, 100], 'color': "lightgray"}],
                     'threshold' : {'line': {'color': color, 'width': 4}, 'thickness': 0.75, 'value': avg_exp_progress}}))

        fig.update_layout(font=dict(color=color))
        
        st.plotly_chart(fig)


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
                target = df.loc[i,'exp_progress']
                fig, ax = plt.subplots()
                fig.set_size_inches(10, 1)
                ax.barh([0], df3.iloc[i,1], align='center', color = '#146C9C')
                ax.get_yaxis().set_visible(False)
                plt.xlim([0,100])
                ax.annotate('%s%%' %(str(df3.iloc[i,1])), (x_coord,-0.1), size = 20, color = color_)
                if df3.iloc[i,-1].days > 0:
                    ax.plot([target, target], [-0.5,0.5], "green")
                    ax.set_title('%s days ahead' %(str(df3.loc[i,'days'].days)), fontsize=18, color='green')
                elif df3.iloc[i,-1].days < 0:
                    ax.plot([target, target], [-0.5,0.5], "red")
                    ax.set_title('%s days late' %(str(df3.loc[i,'days'].days*-1)), fontsize=18, color='red')
                else:
                    ax.plot([target, target], [-0.5,0.5], "black")
                    ax.set_title('On time', fontsize=18)

                st.pyplot(fig)

            df4 = df2.dropna()
            df4 = df4.loc[df4['item_no'] == i+1]
            if len(df4.iloc[:,0]) != 0:
                with st.beta_expander('See remarks'):
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
    sh = gc.open(selected_project)
    df = get_as_dataframe(sh.worksheet('dimension'))
    df.dropna(axis=1, how='all', inplace=True)
    df.dropna(how='all', inplace=True)
    try:
        df2 = get_as_dataframe(sh.worksheet('fact'))
        df2.dropna(axis=1, how='all', inplace=True)
        df2.dropna(how='all', inplace=True)
    except:
        df2 = pd.DataFrame({'item_no':df.iloc[:,0], 'curr_progress':[0]*len(df.iloc[:,0]), 'date':[today]*len(df.iloc[:,0]), 'remarks':['']*len(df.iloc[:,0])})
    try:
        df3 = get_as_dataframe(sh.worksheet('last_submit'))
        df3.dropna(axis=1, how='all', inplace=True)
        df3.dropna(how='all', inplace=True)
    except:
        df3 = pd.DataFrame({'item_no':df.iloc[:,0], 'curr_progress':[0]*len(df.iloc[:,0]), 'date':[today]*len(df.iloc[:,0]), 'remarks':['']*len(df.iloc[:,0])})
    #create empty list for progress and remarks
    prog = []
    remarks = []
    
    with st.form(key='vendor_form'):

        for i in range(len(df.iloc[:,0])):
            c1, c2 ,c3= st.beta_columns([3,1.5,1.5])
            with c1: #list items
                st.write("##")
                st.write(df.iloc[i,1])
    
            with c2: #input progress
                last_value = df3.iloc[i,1].astype('int')
                prog.append(st.number_input("Progress (%)",min_value=0, max_value=100, value=last_value, step=1, key=str(i)))
    
            with c3: #input remarks
                remarks.append(st.text_input('Remarks', key=str((i+1)*10)))
        df3 = pd.DataFrame({'item_no':df.iloc[:,0], 'curr_progress':prog, 'date':[today]*len(df.iloc[:,0]), 'remarks':remarks})
        df2 = df2.append(df3, ignore_index = True)
        
        update_button = st.form_submit_button(label='Update')

    if update_button: #user press Update button
        try:
            set_with_dataframe(sh.worksheet('fact'), df2)
        except:
            sh.add_worksheet(title="fact", rows="10", cols="10")
            set_with_dataframe(sh.worksheet('fact'), df2)
        
        try:
            set_with_dataframe(sh.worksheet('last_submit'), df3)
        except:
            sh.add_worksheet(title="last_submit", rows="10", cols="10")
            set_with_dataframe(sh.worksheet('last_submit'), df3)

        receiver = "akmal.nordi@cima.com.my"
        body = "%s has been updated" %(selected_project)

        yag = yagmail.SMTP("pythonakmal@gmail.com",st.secrets['email']['pwd'])
        yag.send(
            to=receiver,
            subject="DTSF Project Dashboard",
            contents=body,
        )
        st.write('Update successful')
