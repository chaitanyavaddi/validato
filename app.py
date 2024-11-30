from utils import load_styles
import streamlit as st
import requests
import time
import json
import re
import pandas as pd
import altair as alt
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
# from langchain_community.llms import Ollama 
# from pandasai import SmartDataframe


#Setting up App Layout & load custom CSS
st.set_page_config(layout="wide", initial_sidebar_state='expanded')
load_styles()


#************************************** CONSTANTS / TEMPLATES ***********************************************************
_AI_PLACEHOLDER = """
        Hi,

        I'm being trained & hopefully I'll be ready to answer you after a couple of weeks. 

        Happy deploying!

        Thanks,r
        Emit AI

        """

headers = {
        'authority': 'allure.dv.itero.cloud',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cookie': 'ALLURE_TESTOPS_SESSION=dfe6ddf0-fb9e-4449-95fa-b3c384808d75; XSRF-TOKEN=ead6e433-c60b-48d1-9df0-cefeca39a129; _ga=GA1.2.225871832.1700484734',
        'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'x-xsrf-token': 'ead6e433-c60b-48d1-9df0-cefeca39a129',
        'Cookie': 'ALLURE_TESTOPS_SESSION=8f3ee9ca-4a4a-423c-8281-daa457a85cb8; XSRF-TOKEN=021db836-22b9-42bf-8e6e-daf040e5f100'
    }

#READING URL Query Params
param_launch_id = st.query_params.get("id", None)
param_feedback = st.query_params.get("feedback", None)

#************************************** CONSTANTS / TEMPLATES END ***********************************************************




# ************************************ PAGE STATE MANAGEMENT INITIALIZATION **************************************************
if 'passed_count' not in st.session_state:
    st.session_state.passed_count = 0
if 'failed_count' not in st.session_state:
    st.session_state.failed_count = 0
if 'broken_count' not in st.session_state:
    st.session_state.broken_count = 0
if 'launch_name' not in st.session_state:
    st.session_state.launch_name = ""
if 'launch_duration' not in st.session_state:
    st.session_state.launch_duration = ""
# ************************************ PAGE STATE MANAGEMENT INITIALIZATION  END **************************************************




#************************************** GEN AI HELPER METHODS **************************************************
def stream_data():
    for word in _AI_PLACEHOLDER.split(" "):
        yield word + " "
        time.sleep(0.01)
           
@st.dialog("AI Summary", width='large')
def ai_summary(test_name="All Tests Summary"):
    with st.container(border=True):
        layout = st.columns([4, 1])
        
        if test_name !="All Tests Summary":
            with layout[0]:
                st.radio("Generation Mode", options=["Summary", "Bug Description"], horizontal=True, label_visibility='collapsed')
            with layout[1]:
                generate1 = st.button("Generate", type='primary')
            if generate1:
                    st.write_stream(stream_data)
        else:
             with layout[0]:
                 st.write(f'**{test_name}**')
             with layout[1]:
                generate2 = st.button("Generate", type='primary')
             if generate2:
                 st.write_stream(stream_data)
#************************************** GEN AI HELPER METHODS END ***********************************************




#************************************** FEEDBACK FORM START ****************************************************
def read_feedback_file():
    with open('feedback.json', 'r') as file:
        return json.load(file)

def write_feedback_file(data):
    with open('feedback.json', 'w') as file:
        json.dump(data, file, indent=4)

@st.dialog("Feedback")
def feedback_dialog(rating):
    st.caption(f"Thanks for the {rating} rating 😊")
    user_email = st.text_input("", placeholder="Your Email", label_visibility='collapsed')
    user_feedback = st.text_area("", placeholder="Write here..", label_visibility='collapsed')
    if param_feedback:
            with st.expander("User Submissions"):
                st.table(read_feedback_file())
    if st.button("Send", type='primary'):
        # Read the existing feedback
        feedback_data = read_feedback_file()
        new_feedback = {
            "email": user_email,
            "rating": rating,
            "feedback": user_feedback
        }
        
        feedback_data.append(new_feedback)
        write_feedback_file(feedback_data)
        st.success("Feedback submitted successfully!")
#************************************** FEEDBACK FORM END *******************************************************




#************************************** SIDEBAR START ***********************************************************
with st.sidebar:
        st.caption("Click below button to know Allure Launch Summary")
        if st.button("Gen AI Summary", type="secondary"):
                ai_summary()

        #Create space under AI Button
        for i in range(0, 10) :
            st.write("")
        
        #If user submitted feedback, don't render form
        if 'feedback_done' not in st.session_state:
            with st.container(border=True):
                st.caption("Leave us some feedback ❤️")
                sentiment_mapping = ["one", "two", "three", "four", "five"]
                selected = st.feedback("stars")
                if selected is not None:
                    feedback_dialog(sentiment_mapping[selected])
                    st.session_state.feedback_done = True
#************************************** SIDEBAR END ***********************************************************




#************************************** FORMATTING HELPER METHODS **********************************************
def extract_json_from_string(s):
    # Regular expression to find JSON-like structures
    json_pattern = re.compile(r'\{.*?\}')
    match = json_pattern.search(s)
    
    if match:
        try:
            # Parse the JSON string
            json_data = json.loads(match.group())
            return json_data
        except json.JSONDecodeError:
            return None
    return None

# Function to format duration in minutes and seconds
def format_duration(duration_ms):
    if duration_ms:
        minutes, seconds = divmod(duration_ms // 1000, 60)
        return f"{minutes}m {seconds}s"

def clear_textarea_callback():
    st.session_state["launch_urls"] = ""

def is_valid_allure_link(link):
        if link.startswith("https://allure.dv.itero.cloud/launch/"):
            return True
        st.toast("Invalid Link")
        return False
#************************************** FORMATTING HELPER METHODS END **********************************************





#************************************** ALLURE API CALLS ***********************************************************
def fetch_launch_ids(search_phrase):
    url = f'https://allure.dv.itero.cloud/api/rs/launch?search={search_phrase}&projectId=15&page=0&size=10'
    response = requests.get(url, headers=headers)
    return response.json()

@st.cache_data
def fetch_all_testresults(launch_id):
    url = f"https://allure.dv.itero.cloud/api/rs/testresult?launchId={launch_id}&page=0&size=500&sort=createdDate%2CDESC"
    response = requests.get(url, headers=headers)
    return response.json()

@st.cache_data
def fetch_test_results(launch_id):
    url = f"https://allure.dv.itero.cloud/api/rs/testresulttree/leaf?launchId={launch_id}&&sort=name%2Casc&size=100"
    response = requests.get(url, headers=headers)
    return response.json()

@st.cache_data
def fetch_duration(launch_id):
    url = f"https://allure.dv.itero.cloud/api/rs/launch/{launch_id}/duration"
    response = requests.get(url, headers=headers)
    r= response.json()
    return r[-1]['duration']

@st.cache_data
def fetch_launch_name(launch_id):
    url = f"https://allure.dv.itero.cloud/api/rs/launch/__search?projectId=15&rql=id%3D%27{launch_id}%27&page=0&size=10&sort=created_date%2CDESC"
    response = requests.get(url, headers=headers)
    r = response.json()
    return r["content"][0]["name"]

def fetch_launch_details(launch_id):
    url = f"https://allure.dv.itero.cloud/api/rs/launch/{launch_id}"
    response = requests.get(url, headers=headers)
    r = response.json()
    return r["tags"]

def fetch_launch_status(launch_id):
    url = f"https://allure.dv.itero.cloud/api/rs/launch/{launch_id}/statistic"
    response = requests.get(url, headers=headers)
    return response.json()

def read_allure_attachment(attachment_id):
     url = f"https://allure.dv.itero.cloud/api/rs/testresult/attachment/{attachment_id}/content"
     response = requests.get(url, headers=headers)
     return response

def fetch_test_execution_steps(test_tree_id):
     url = f"https://allure.dv.itero.cloud/api/rs/testresult/{test_tree_id}/execution"
     response = requests.get(url, headers=headers)
     return response.json()
#************************************** ALLURE API CALLS END ***********************************************************




#************************************** PAGE RESUSABLE BLOCKS START ***********************************************************
def update_metric_counts(launch_id):
    st.session_state.passed_count = 0
    st.session_state.failed_count = 0
    st.session_state.broken_count = 0
    data = fetch_launch_status(launch_id)
    
    for item in data:
        if item['status'] == 'failed':
            st.session_state.failed_count = item['count']
        if item['status'] == 'passed':
            st.session_state.passed_count = item['count']
        if item['status'] == 'broken':
            st.session_state.broken_count = item['count']

def display_steps(steps):
    stack = [(steps, 0)]
    while stack:
        current_steps, level = stack.pop()
        for step in current_steps:
            if isinstance(step, dict):
                status_icon = "✔" if step.get("status") == "passed" else "❌"
                st.write(" " * level * 4 + f"{status_icon} {step.get('name', 'Unnamed Step')}")
                if "steps" in step and isinstance(step["steps"], list) and step["steps"]:
                    stack.append((step["steps"], level + 1))

@st.dialog("Test Comparision", width='large')
def open_test_compare_window(test_name, launch_name):
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader(f"{launch_name}")
            with st.spinner("Processing.."):
                steps =  fetch_test_execution_steps(373937661)
                # display_steps(r)
                stack = [(steps, 0)]
                while stack:
                    current_step, level = stack.pop()
                    if isinstance(current_step, dict):
                            status_icon = "✔" if current_step.get("status") == "passed" else "❌"
                            st.markdown(f"<div style='margin-left: {level * 20}px'>{status_icon} {current_step.get('name', 'Unnamed Step')}</div>", unsafe_allow_html=True)
                            if "steps" in current_step and isinstance(current_step["steps"], list) and current_step["steps"]:
                                if level < 1:
                                    for step in reversed(current_step["steps"]):
                                        stack.append((step, level + 1))
    with col2:
        with st.container(border=True):
            st.subheader("Last Passed (2 days back)")
            st.write("Passed that day")  
#**************************************  PAGE RESUSABLE BLOCKS END *********************************************************************************




#**************************************  PAGE TOP SECTION: TEXT INPUT, BUTTON, METRIC CARDS ***********************************************************
sub_cols = st.columns([4, 1.8, 3,  2, 2, 2])

# Input for allure links
with st.container(border=True):
    with sub_cols[0]:
        launch_name = st.empty()
        launch_name.write("**Allure Test Results Analyser**")

        if param_launch_id:
            allure_links = st.text_input('Enter Allure Link', label_visibility='collapsed', key="allure_link", value=f"https://allure.dv.itero.cloud/launch/{param_launch_id}")
        else:
            allure_links = st.text_input('Enter Allure Link', "", placeholder="Eg. https://allure.dv.itero.cloud/launch/423801", label_visibility='collapsed', key="allure_link")

    with sub_cols[1]:
        analyse_button = st.button('Analyze', key='is_analysed', type='primary')
        if param_launch_id:
            analyse_button = True
    
report_mode_tabs = st.tabs(["360° Overview"])

cols = st.columns([1, 5, 1])

with cols[1]:
    with report_mode_tabs[0]:  

        # When the analyze button is clicked
        if analyse_button:
            try:
                links = allure_links.split('\n')
                launch_ids = [link.split('/')[-1] for link in links if is_valid_allure_link(link)]

                if len(launch_ids) > 0:
                    launch_id = launch_ids[0]
                    launch_name     = fetch_launch_name(launch_id)
                    launch_duration = fetch_duration(launch_id)
                    st.session_state.launch_name = launch_name
                    st.session_state.launch_duration = format_duration(int(launch_duration))
                    update_metric_counts(launch_id=launch_id)
                    test_results = fetch_all_testresults(launch_id)
               
                    #************************************ CORE LOGIC START - TEST RESULTS TO PANDAS DATAFRME **************************************************
                    table_data = []
                    for item in test_results['content']:
                        test_name = item.get('name')
                        status = item['status']
                        duration = format_duration(item['duration'] if item.get('duration') else None)
                        message = item.get('message', '')
                        api_failure = ''
                        response_code = ''
                        trace_id = ''
                        signal_fx = ''
                        
                        if 'Response error:' in message:
                            message_json = extract_json_from_string(message)
                            api_failure = message_json.get('url', '')
                            response_code = message_json.get('status_code', '')
                            trace_id = message_json.get('x-trace', '')
                            if trace_id:
                                signal_fx = f"https://aligntech.signalfx.com/#/apm/traces/{trace_id.split(':')[0]}"
                        
                        
                        trace_button = item["trace"] if item.get("trace") else '-'
                        job_logs = item["jobRun"]["url"] if item.get("jobRun") else '-'
                        host_id = item['hostId']     if item.get("hostId") else '-'
                        thread_id = item['threadId'] if item.get("threadId") else '-'
                        procedure = item['fullName'].split('.')[2] if  "." in item.get("fullName") else '-'
                        jama_link = item['links'][0]['url'] if item.get("links") else ''
                        author = "https://teams.microsoft.com/l/chat/0/0?users=scheekati@aligntech.com"
                        test_tree_id = f"https://allure.dv.itero.cloud/launch/{launch_id}/tree/{item.get('id')}" 
                        
                        
                        region = '-'
                        if '~ -US' in test_name:
                            region = 'US'
                        elif '~ -EU' in test_name:
                            region = 'EU'
                        elif '~ -CN' in test_name:
                            region = 'CN'
                        elif '~ -AP' in test_name:
                            region = 'AP'
                        
                        table_data.append([test_name, status, duration, region, procedure, test_tree_id, job_logs, jama_link, message, api_failure, signal_fx, trace_button, response_code, trace_id, host_id, thread_id])

                        # Create DataFrame
                        columns = ['Test Name', 'Status', 'Duration', 'Region', 'Procedure', 'Allure Report', 'Jenkins Logs', 'JAMA Link', 'Message', 'Api Failure', 'Signalfx','Trace', 'Response Code', 'Trace ID',  'Host ID', 'Thread ID']
                        
                        df = pd.DataFrame(table_data, columns=columns)

                        st.session_state["dataframe"] = df
                    #************************************ CORE LOGIC END - TEST RESULTS TO PANDAS DATAFRME **************************************************

            except Exception as e:
                    st.toast("Invalid link / something off with Allure")

        #************************************ CORE LOGIC START - RENDER DATAFRAME, & CHARTS USING AGGRID **************************************************
        if "dataframe" in st.session_state:
                with sub_cols[2]:
                        with st.container(border=True):
                            st.metric(f"{st.session_state.launch_name}", "PPR", delta=f"{st.session_state.launch_duration}", delta_color='off')

                with sub_cols[3]:
                    with st.container(border=True):
                        st.metric("Passed", f"{st.session_state.passed_count}", delta=f"{st.session_state.passed_count}")
                    
                with sub_cols[4]:
                    with st.container(border=True):
                        st.metric("Failed", "", delta=f"{st.session_state.failed_count}", delta_color='inverse')
                    
                with sub_cols[5]:
                        with st.container(border=True):
                            st.metric("Broken", 0, delta=f"{st.session_state.broken_count}", delta_color="off")

                #CAUTION START: ANY CONFIG CHANGE HERE COULD BREAK UI***************************           
                gb = GridOptionsBuilder.from_dataframe(st.session_state.dataframe)
                cell_renderer = JsCode("""
                class UrlCellRenderer {
                    init(params) {
                        const url = params.value;
                        let displayText = "NA";
                        if (url.includes('jama')) {
                            const parts = url.split('/');
                            displayText = parts[parts.length - 1].substring(0, 6);
                        } else if (url.includes('/job/')) {
                            const parts = url.split('/');
                            displayText = parts[parts.length - 2];
                        } else if (url.includes('/tree/') || url.includes('signalfx')) {
                            displayText = "Click here";
                        }
                        this.eGui = document.createElement('a');
                        this.eGui.innerText = displayText;
                        this.eGui.setAttribute('href', params.value);
                        this.eGui.setAttribute('style', "text-decoration:none");
                        this.eGui.setAttribute('target', "_blank");
                    }
                    getGui() {
                        return this.eGui;
                    }
                }
            """)

                cellsytle_jscode = JsCode("""
                    function(params){
                        if (params.value === 'passed') {
                            return {
                                'color': 'white', 
                                'backgroundColor': '#5c9f1d',
                            }
                        } else if (params.value === 'failed'){
                            return {
                                'color': 'white', 
                                'backgroundColor': '#ff3434',
                            }
                        } else if (params.value === 'broken'){
                            return {
                                'color': 'white', 
                                'backgroundColor': 'orange',
                            }
                        }
                    }
                """)
                
                gb.configure_column("Test Name", pinned='left')
                gb.configure_column("Jenkins Logs", width=100, cellRenderer=cell_renderer)
                gb.configure_column("JAMA Link", width=100, cellRenderer=cell_renderer)
                gb.configure_column("Allure Report", width=100, cellRenderer=cell_renderer)
                gb.configure_column("Signalfx", width=100, cellRenderer=cell_renderer)
                gb.configure_grid_options(enableCellTextSelection=True, enableRangeSelection=True)
                gb.configure_default_column(filter=True, cellStyle=cellsytle_jscode, wrapText=True)
                gb.configure_selection('single', use_checkbox=True)
                gridOptions = gb.build()
                #CAUTION END: ANY CONFIG CHANGE HERE COULD BREAK UI********************************************************* 

                response = AgGrid(st.session_state.dataframe, gridOptions=gridOptions, enable_enterprise_modules=False, height=500, updateMode=GridUpdateMode.MODEL_CHANGED, allow_unsafe_jscode=True, data_return_mode='FILTERED')
                
                filtered_df = pd.DataFrame(response['data'])

                selected_rows = response['selected_rows']
                
                st.subheader(f"**Filtered Row Count: {len(filtered_df)}**", divider="gray", help="Filter above table to understand specific set of tests")
                
                chart_layout = st.columns(3)
                
                #*********************ALTAIR CHART: Test Status by Procedure******************
                with chart_layout[0]:
                    procedure_chart = alt.Chart(filtered_df).mark_bar().encode(
                        x='Procedure',
                        y='count()',
                        color='Status'
                    ).properties(
                        title='Test Status by Procedure'
                    )
                    st.altair_chart(procedure_chart, use_container_width=True)
                #*****************************************************************************



                
                #*********************ALTAIR CHART: Test Status by Region**********************
                with chart_layout[1]:
                    region_chart = alt.Chart(filtered_df).mark_bar().encode(
                        x='Region',
                        y='count()',
                        color='Status'
                    ).properties(
                        title='Test Status by Region'
                    )
                    st.altair_chart(region_chart, use_container_width=True)
                #*****************************************************************************************



                
                #*********************ALTAIR CHART: Test Status by Host ID********************************************
                with chart_layout[2]:
                    host_chart = alt.Chart(filtered_df).mark_bar().encode(
                        x='Host ID',
                        y='count()',
                        color='Status'
                    ).properties(
                        title='Test Status by Host ID'
                    )
                    st.altair_chart(host_chart, use_container_width=True)
                #******************************************************************************************************



                
                chart_layout_two = st.columns([2, 2, 1])

                #*********************ALTAIR CHART: Failures by API Host and Status Code********************************
                with chart_layout_two[0]:
                    
                    failed_apis = filtered_df[filtered_df['Status'] == 'failed']
                    
                    def extract_host_part(url):
                        if pd.notna(url):
                            parts = url.split('/')
                            if len(parts) > 2:
                                return parts[2]
                        return 'Non API Failure'
                    
                    failed_apis['Host Part'] = failed_apis['Api Failure'].apply(extract_host_part)
                    
                    status_counts = failed_apis.groupby(['Host Part', 'Response Code']).size().reset_index(name='count')
                    
                    status_counts = status_counts[status_counts['Host Part'] != 'Non API Failure']

                    bar_chart = alt.Chart(status_counts).mark_bar().encode(
                        x='Host Part',
                        y='count',
                        color='Response Code',
                        tooltip=['Host Part', 'Response Code', 'count']
                    ).properties(
                        title='Failures by API Host and Status Code'
                    )
                    st.altair_chart(bar_chart, use_container_width=True)
                #***********************************************************************************************************



                
                #*********************ALTAIR CHART: Failures by API Status Code vs Non-API Related**************************
                with chart_layout_two[1]:
                    # API Failures Percentage
                    
                    # Filter the DataFrame for failed tests
                    failed_tests = filtered_df[filtered_df['Status'] == 'failed']

                    # Categorize failures based on the "Api Failure" column
                    failed_tests['Failure Type'] = failed_tests['Api Failure'].apply(lambda x: 'API Failure' if pd.notna(x) and x != '' else 'Non-API Failure')

                    # Count the occurrences of each failure type
                    failure_counts = failed_tests['Failure Type'].value_counts().reset_index()
                    failure_counts.columns = ['Failure Type', 'Test Count']

                    # Create the pie chart
                    pie_chart = alt.Chart(failure_counts).mark_arc().encode(
                        theta=alt.Theta(field='Test Count', type='quantitative'),
                        color=alt.Color(field='Failure Type', type='nominal'),
                        tooltip=['Failure Type', 'Test Count']
                    ).properties(
                        title='Failures by API Status Code vs Non-API Related '
                    )

                    # Display the pie chart
                    st.altair_chart(pie_chart, use_container_width=True)
                #***********************************************************************************************************


                

                #*********************QUICK LINKS*********************************************
                with chart_layout_two[2]:
                    with st.container(border=True):
                        st.markdown("Need help? Check the wiki Links")
                        st.link_button("Component Owners ↗", url="https://wiki.aligntech.com/pages/viewpage.action?spaceKey=iKMSSYSFLOWS&title=Must+Pass+Runbook+-+SFA+Incident+Management#table-filter-1724089458655", type='primary')
                        st.link_button("PPR Bugs ↗", url="https://wiki.aligntech.com/display/RIAC/Deprecated+CI+SF+Open+Issues", type='primary')
                        st.link_button("QAS Bugs ↗", url="https://jira.aligntech.com/issues/?jql=labels%20%3D%20QAS_bugs", type='primary')
                        st.link_button("Run Book ↗", url="https://wiki.aligntech.com/pages/viewpage.action?spaceKey=iKMSSYSFLOWS&title=Must+Pass+Runbook+-+SFA+Incident+Managemen", type='primary')
                        st.link_button("Mustpass Support ↗", url=f"mailto:cvaddisriram@aligntech.com; rkhare@aligntech.com; scheekati@aligntech.com; sukanya.singh@aligntech.com?cc=s-khan@aligntech.com;&subject=EMIT%3A%20Query%20regarding%20{st.session_state.launch_name}", type='primary')
                #******************************************************************************


                
              
                #*********************IMPACTED TEST CASES SECTION******************************
                st.subheader("Impacted Test Cases",divider='grey')
                failed_apis_filtered = failed_apis[failed_apis['Api Failure'] != '']
                impacted_tests = failed_apis_filtered[['Test Name', 'Api Failure', 'Response Code', 'Signalfx', 'Allure Report']]
                
                impacted_columns = st.columns(1)
                with impacted_columns[0]:
                    st.write("Failed due to API Response Codes:")
                    st.dataframe(impacted_tests, column_config={
                        "Allure Report": st.column_config.LinkColumn(display_text="Click here"),
                        "Signalfx": st.column_config.LinkColumn(display_text="Click here")
                    }, use_container_width=True)

                non_api_failures_df = failed_tests[failed_tests['Failure Type'] == 'Non-API Failure'][['Test Name', 'Message', 'Trace']]
                st.write("Failed Tests Not Related to API Failures:")
                st.dataframe(non_api_failures_df, use_container_width=True)
                st.divider()
                #******************************************************************************

        #************************************ CORE LOGIC END - RENDER DATAFRAME, & CHARTS USING AGGRID **************************************************  

        
                   

                # st.dataframe(filtered_df)
                    # llm = Ollama(model="mistral")
                    # df2 = SmartDataframe(st.session_state.dataframe, config={"llm": llm})
                    # prompt = st.text_area("Enter your prompt:")
                    # if st.button("Generate"):
                    #     if prompt:
                    #         with st.spinner("Generating response..."):
                    #             st.write(df2.chat(prompt))
                    #     else:
                    #         st.warning("Please enter a prompt!")


                # Fetch the content from the URL
                # responses = read_allure_attachment()
                # text_content = responses.text

                # # Display the content in Streamlit
                # st.text_area("Text File Content", text_content, height=300)

