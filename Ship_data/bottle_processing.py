# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.4'
#       jupytext_version: 1.2.4
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# # Bottle Processing
# Author: Andrew Reed
#
# ### Motivation:
# Independent verification of the suite of physical and chemical observations provided by OOI are critical for the observations to be of use for scientifically valid investigations. Consequently, CTD casts and Niskin water samples are made during deployment and recovery of OOI platforms, vehicles, and instrumentation. The water samples are subsequently analyzed by independent labs for  comparison with the OOI telemetered and recovered data.
#
# However, currently the water sample data routinely collected and analyzed as part of the OOI program are not available in a standardized format which maps the different chemical analyses to the physical measurements taken at bottle closure. Our aim is to make these physical and chemical analyses of collected water samples available to the end-user in a standardized format for easy comprehension and use, while maintaining the source data files. 
#
# ### Approach:
# Generating a summary of the water sample analyses involves preprocessing and concatenating multiple data sources, and accurately matching samples with each other. To do this, I first preprocess the ctd casts to generate bottle (.btl) files using the SeaBird vendor software following the SOP available on Alfresco. 
#
# Next, the bottle files are parsed using python code and the data renamed following SeaBird's naming guide. This creates a series of individual cast summary (.sum) files. These files are then loaded into pandas dataframes, appended to each other, and exported as a csv file containing all of the bottle data in a single data file.
#
# ### Data Sources/Software:
#
# * **sbe_name_map**: This is a spreadsheet which maps the short names generated by the SeaBird SBE DataProcessing Software to the associated full names. The name mapping originates from SeaBird's SBE DataProcessing support documentation.
#
# * **Alfresco**: The Alfresco CMS for OOI at alfresco.oceanobservatories.org is the source of the ctd hex, xmlcon, and psa files necessary for generating the bottle files needed to create the sample summary sheet.
#
# * **SBEDataProcessing-Win32**: SeaBird vendor software for processing the raw ctd files and generating the .btl files.
#

import os, sys, re
import pandas as pd
import numpy as np

sbe_name_map = pd.read_excel('/media/andrew/OS/Users/areed/Documents/OOI-CGSN/QAQC_Sandbox/Reference_Files/seabird_ctd_name_map.xlsx')

sbe_name_map.head()

# **========================================================================================================================**
# Declare the directory paths to where the relevant information is stored:

basepath = '/home/andrew/Documents/OOI-CGSN/QAQC_Sandbox/Ship_data/'

os.listdir(basepath+'Pioneer')

basepath = '/home/andrew/Documents/OOI-CGSN/QAQC_Sandbox/Ship_data/'
array = 'Pioneer/'
cruise =   'Pioneer-07_AR-08_2016-09-27/'

sorted(os.listdir(basepath+array+cruise))

water = 'Water Sampling/'
ctd = 'ctd/'
leg = 'Leg 2 (ar08b)/'

sorted(os.listdir(basepath+array+cruise+water))

sample_dir = basepath + array + cruise + leg + ctd
water_dir = basepath + array + cruise + water
log_path = water_dir + 'Pioneer-07_AR-08B_CTD_Sampling_Log.xlsx'
chl_path = water_dir + ''
dic_path = water_dir + ''
nutrients_path = water_dir + 'Pioneer-07_AR-08_Nutrients_Sample_Data_2019-11-12_ver_1-00.xlsx'
salts_and_o2_path = water_dir + 'Pioneer-07_AR-08B_Oxygen_Salinity_Sample_Data/'


# **===================================================================================================================**

# Parse the data for the start_time
def parse_header(header):
    """
    Parse the header of bottle (.btl) files to get critical information
    for the summary spreadsheet.
    
    Args:
        header - an object containing the header of the bottle file as a list of
            strings, split at the newline.
    Returns:
        hdr - a dictionary object containing the start_time, filename, latitude,
            longitude, and cruise id.
    """
    hdr = {}
    for line in header:
        if 'nmea utc' in line.lower():
            start_time = pd.to_datetime(re.split('= |\[',line)[1])
            hdr.update({'Start Time [UTC]':start_time.strftime('%Y-%m-%dT%H:%M:%SZ')})
        elif 'filename' in line.lower():
            hex_name = re.split('=',line)[1].strip()
            hdr.update({'Filename':hex_name})
        elif 'nmea latitude' in line.lower():
            start_lat = re.split('=',line)[1].strip()
            hdr.update({'Start Latitude [degrees]':start_lat})
        elif 'nmea longitude' in line.lower():
            start_lon = re.split('=',line)[1].strip()
            hdr.update({'Start Longitude [degrees]':start_lon})
        elif 'cruise id' in line.lower():
            cruise_id = re.split(':',line)[1].strip()
            hdr.update({'Cruise':cruise_id})
        else:
            pass
    
    return hdr


# Get the path to the ctd-bottle data, load it, and parse it:

# Now write a function to autopopulate the bottle summary sample sheet
files = [x for x in os.listdir(sample_dir) if '.btl' in x]
for filename in files:
    filepath = os.path.abspath(sample_dir+filename)
    
    # Load the raw content into memory
    with open(filepath) as file:
        content = file.readlines()
    content = [x.strip() for x in content]
    
    # Now parse the file content
    header = []
    columns = []
    data = []
    for line in content:
        if line.startswith('*') or line.startswith('#'):
            header.append(line)
        else:
            try:
                float(line[0])
                data.append(line)
            except:
                columns.append(line)
                
    # Parse the header
    hdr = parse_header(header)
    
    # Parse the column identifiers
    column_dict = {}
    for line in columns:
        for i,x in enumerate(line.split()):
            try:
                column_dict[i] = column_dict[i] + ' ' + x
            except:
                column_dict.update({i:x})
                
    #Parse the bottle data based on the column header locations
    data_dict = {x:[] for x in column_dict.keys()}

    for line in data:
        if line.endswith('(avg)'):
            values = list(filter(None,re.split('  |\t', line) ) )
            for i,x in enumerate(values):
                data_dict[i].append(x)
        elif line.endswith('(sdev)'):
            values = list(filter(None,re.split('  |\t', line) ) )
            data_dict[1].append(values[0])
        else:
            pass
    
    # Join the date and time for each measurement into a single item
    data_dict[1] = [' '.join(item) for item in zip(data_dict[1][::2],data_dict[1][1::2])]
    
    # With the parsed data and column names, match up the data and column
    # based on the location
    results = {}
    for key,item in column_dict.items():
        values = data_dict[key]
        results.update({item:values})
        
    # Put the results into a dataframe
    df = pd.DataFrame.from_dict(results)

    # Now add the parsed info from the header files into the dataframe
    for key,item in hdr.items():
        df[key] = item
        
    # Get the cast number
    cast = filename[filename.index('.')-3:filename.index('.')]
    df['Cast'] = str(cast).zfill(3)
    
    # Add the header info back in
    for key in hdr.keys():
        df[key] = hdr[key]
        
    # Generate a filename for the summary file
    outname = filename.split('.')[0] + '.sum'
    
    # Save the results
    df.to_csv(sample_dir+outname)

# Now, for each "summary" file, load and append to each other
df = pd.DataFrame()
for file in os.listdir(sample_dir):
    if '.sum' in file:
        df = df.append(pd.read_csv(sample_dir+file))
    else:
        pass

# Rename the column title using the sbe_name_mapping 
for colname in list(df.columns.values):
    try:
        fullname = list(sbe_name_map[sbe_name_map['Short Name'].apply(lambda x: str(x).lower() == colname.lower()) == True]['Full Name'])[0]
        df.rename({colname:fullname},axis='columns',inplace=True)
    except:
        pass


# **========================================================================================================================**
# ### Process the Discrete Salinity and Oxygen Data
# Next, I process the discrete salinity and oxygen sample data so that it is consistently named and ready to be merged with the existing data sets.

# +
def clean_sal_files(dirpath):

    # Run check if files are held in excel format or csvs
    csv_flag = any(files.endswith('.SAL') for files in os.listdir(dirpath))
    if csv_flag:
        for filename in os.listdir(dirpath):
            sample = []
            salinity = []
            if filename.endswith('.SAL'):
                with open(dirpath+filename) as file:
                    data = file.readlines()
                    for ind1,line in enumerate(data):
                        if ind1 == 0:
                            strs = data[0].replace('"','').split(',')
                            cruisename = strs[0]
                            station = strs[1]
                            cast = strs[2]
                            case = strs[8]
                        elif int(line.split()[0]) == 0:
                            pass
                        else:
                            strs = line.split()
                            sample.append(strs[0])
                            salinity.append(strs[2])
                
                    # Generate a pandas dataframe to populate data
                    data_dict = {'Cruise':cruisename,'Station':station,'Cast':cast,'Case':case,'Sample ID':sample,'Salinity [psu]':salinity}
                    df = pd.DataFrame.from_dict(data_dict)
                    df.to_csv(file.name.replace('.','')+'.csv')
            else:
                pass
    
    else:
        # If the files are already in excel spreadsheets, they've been cleaned into a
        # logical tabular format
        pass
    

def process_sal_files(dirpath):
    
    # Check if the files are excel files or not
    excel_flag = any(files.endswith('SAL.xlsx') for files in os.listdir(dirpath))
    # Initialize a dataframe for processing the salinity files
    df = pd.DataFrame()
    if excel_flag:
        for file in os.listdir(dirpath):
            if 'SAL.xlsx' in file:
                df = df.append(pd.read_excel(dirpath+file))
        df.rename({'Sample':'Sample ID','Salinity':'Salinity [psu]','Niskin #':'Niskin','Case ID':'Case'}, 
                  axis='columns',inplace=True)
        df.dropna(inplace=True)
        df['Station'] = df['Station'].apply(lambda x: str( int(x)).zfill(3))
        df['Niskin'] = df['Niskin'].apply(lambda x: str( int(x)))
        df['Sample ID'] = df['Sample ID'].apply(lambda x: str( int(x)))
    else:
        for file in os.listdir(dirpath):
            if 'SAL.csv' in file:
                df = df.append(pd.read_csv(dirpath+file))
        df.dropna(inplace=True)
        df['Station'] = df['Station'].apply(lambda x: str( int(x)).zfill(3))
        df['Sample ID'] = df['Sample ID'].apply(lambda x: str( int(x)))
        df.drop(columns=[x for x in list(df.columns.values) if 'unnamed' in x.lower()],inplace=True)

    # Save the processed summary file for salinity
    df.to_csv(dirpath+'SAL_Summary.csv')
    
    
def process_oxy_files(dirpath):
    df = pd.DataFrame()
    for filename in os.listdir(dirpath):
        if 'oxy' in filename.lower() and filename.endswith('.xlsx'):
            df = df.append(pd.read_excel(dirpath+filename)) 
            # Rename and clean up the oxygen data to be uniform across data sets
    df.rename({'Niskin #':'Niskin','Sample#':'Sample ID','Oxy':'Oxygen [mL/L]','Unit':'Units'},
              axis='columns',inplace=True)
    df.dropna(inplace=True)
    df['Station'] = df['Station'].apply(lambda x: str( int(x)).zfill(3))
    #df['Niskin'] = df['Niskin'].apply(lambda x: str( int(x)))
    df['Sample ID'] = df['Sample ID'].apply(lambda x: str( int(x)))
    df['Cruise'] = df['Cruise'].apply(lambda x: x.replace('O','0'))
    
    # Save the processed summary file for oxygen
    df.to_csv(dirpath+'OXY_Summary.csv')


# -

# Now process the salts and oxygen data
    # Clean the salinity
clean_sal_files(salts_and_o2_path)
    # Process the salinity files
process_sal_files(salts_and_o2_path)
    # Process the oxygen files
process_oxy_files(salts_and_o2_path)

# **===================================================================================================================**
# ### Load the Sampling Log 

# Load the CTD Log csv
log = pd.read_excel(log_path, sheet_name='Summary')
# Add "Log" to the column name
for colname in list(log.columns.values):
    log.rename(columns={colname:'Log: '+colname}, inplace=True)
log.rename(columns={'Log:  Oxygen Bottle #':'Log: Oxygen Bottle #'}, inplace=True)

log.head()

log["Log: Start Time"] = log["Log: Start Time"].apply(str)

log["Log: Start Time"] = log["Log: Start Time"].apply(lambda x: pd.to_datetime(x,format='%H%M') if type(x) == str else x)
# Next, need to reformat the Date and Time columns to be pandas datetime objects and merge into a single column
log['Log: Start Date'] = log['Log: Start Date'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d') if not pd.isnull(x) else '')
log['Log: Start Time'] = log['Log: Start Time'].apply(lambda x: x.strftime('%H:%M:%SZ') if not pd.isnull(x) else '00:00:00Z')
# Now combine the two columns into a single column
log['Log: Start Date'] = log['Log: Start Date'] + 'T' + log['Log: Start Time']
# Check if any start with "T" indicating no date - will replace with ''
log['Log: Start Date'] = log['Log: Start Date'].apply(lambda x: '' if x.startswith('T') else x)
# Drop the "Start Time" column because it is not needed
log.drop(columns='Log: Start Time', inplace=True)

# Now get the cruise id
cruise_id = log[log["Log: Cruise ID"].notna()]["Log: Cruise ID"].unique()[0]
cruise_id

# **If there is no sampling log (but ctd casts)**:

columns = ['Log: Cruise ID', 'Log: Station-Cast #', 'Log: Target Asset', 'Log: Start Latitude', 
           'Log: Start Longitude', 'Log: Start Date', 'Log: Start Time', 'Log: Bottom Depth [m]', 
           'Log: Date', 'Log: Niskin #', 'Log: Time', 'Log: Trip Depth', 'Log: Oxygen Bottle #',
           'Log: Ph Bottle #', 'Log: DIC/TA Bottle #', 'Log: Salts Bottle #', 'Log: Nitrate Bottle 1',
           'Log: Chlorophyll Brown Bottle #', 'Log: Chlorophyll Filter Sample #', 
           'Log: Chlorophyll Brown Bottle Volume', 'Log: Chlorophyll LN Tube', 'Log: Comments']

log = pd.DataFrame(columns=columns)

# ### Duplicate Samples
# Next, want to identify where there are duplicate samples for salts, oxygen, chlorophyll, and nutrients. The process is to:
# 1. Map duplicate samples into a list
# 2. Split the list into rows so each row has an unique entry from the list, copying all other column values
# 3. Identify which rows where copied
# 4. Create a new boolean column indicating the columns copied for each water property sample 

# Salts Duplicates:

# Next, we need to turn any salts duplicates into a list, map the list into rows with unique entries, then identify
# those rows which were copied
log['Log: Salts Bottle #'] = log['Log: Salts Bottle #'].apply(lambda x: x.replace(' ','').split(',') if type(x) == str else x)
# Put each sample into its own row
log = log.explode(column='Log: Salts Bottle #')
# Identify where the indices where duplicated, indicating copying
log["Log: Salts Duplicate"] = log.index.duplicated(keep=False)
# Drop rows which are duplicates (but not necessarily duplicate indices)
log = log.drop_duplicates()
# Reset the index to wipe the memory
log = log.reset_index(drop=True)
# Check for rows which were duplicate samples
log[log["Log: Salts Duplicate"]]

# Oxygen Duplicates:

log['Log: Oxygen Bottle #'] = log['Log: Oxygen Bottle #'].apply(lambda x: x.replace(' ','').split(',') if type(x) == str else x)
# Put each sample into its own row
log = log.explode(column='Log: Oxygen Bottle #')
# Identify where the indices where duplicated, indicating copying
log["Log: Oxygen Duplicate"] = log.index.duplicated(keep=False)
# Drop rows which are duplicates (but not necessarily duplicate indices)
log = log.drop_duplicates()
# Reset the index to wipe the memory
log = log.reset_index(drop=True)
# Check for rows which were duplicate samples
log[log["Log: Oxygen Duplicate"]]

# Nitrate Duplicates:

log['Log: Nitrate Bottle 1'] = log['Log: Nitrate Bottle 1'].apply(lambda x: x.replace(' ','').split(',') if type(x) == str else x)
# Put each sample into its own row
log = log.explode(column='Log: Nitrate Bottle 1')
# Identify where the indices where duplicated, indicating copying
log["Log: Nitrate Duplicate"] = log.index.duplicated(keep=False)
# Drop rows which are duplicates (but not necessarily duplicate indices)
log = log.drop_duplicates()
# Reset the index to wipe the memory
log = log.reset_index(drop=True)
# Check for rows which were duplicate samples
log[log["Log: Nitrate Duplicate"]]

# Chlorophyll Brown Bottle Duplicates:

log['Log: Chlorophyll Brown Bottle #'] = log['Log: Chlorophyll Brown Bottle #'].apply(lambda x: x.replace(' ','').split(',') if type(x) == str else x)
# Put each sample into its own row
log = log.explode(column='Log: Chlorophyll Brown Bottle #')
# Identify where the indices where duplicated, indicating copying
log["Log: Chlorophyll Duplicate"] = log.index.duplicated(keep=False)
# Drop rows which are duplicates (but not necessarily duplicate indices)
log = log.drop_duplicates()
# Reset the index to wipe the memory
log = log.reset_index(drop=True)
# Check for rows which were duplicate samples
log[log["Log: Chlorophyll Duplicate"]]

# Chlorophyll Filter Sample Duplicates:

log['Log: Chlorophyll Filter Sample #'] = log['Log: Chlorophyll Filter Sample #'].apply(lambda x: x.replace(' ','').split(',') if type(x) == str else x)
# Put each sample into its own row
log = log.explode(column='Log: Chlorophyll Filter Sample #')
# Identify where the indices where duplicated, indicating copying
log["Log: Chlorophyll Filter Duplicate"] = log.index.duplicated(keep=False)
# Drop rows which are duplicates (but not necessarily duplicate indices)
log = log.drop_duplicates()
# Reset the index to wipe the memory
log = log.reset_index(drop=True)
# Check for rows which were duplicate samples
log[log["Log: Chlorophyll Filter Duplicate"]]

log.shape

# **===================================================================================================================** 
# ### Salinity & Oxygen Data
# Next, add in the salinity and oxygen data to the log, keying off of the sample bottles

sal = pd.read_csv(salts_and_o2_path+'SAL_Summary.csv')
sal.drop(columns={'Unnamed: 0'}, inplace=True)
# Rename the columns to name source
for colname in list(sal.columns.values):
    sal.rename(columns={colname: 'Sal: ' + colname}, inplace=True)
sal['Sal: Salts Bottle #'] = sal['Sal: Case'] + sal['Sal: Sample ID'].apply(lambda x: str(x))
sal.drop(columns=['Sal: Sample ID','Sal: Case'], inplace=True)
# Check out the salinity data
sal.head()

# Load the oxygen data
oxy = pd.read_csv(salts_and_o2_path+'OXY_Summary.csv')
oxy.drop(columns={'Unnamed: 0'}, inplace=True)
# Rename the columns to name the source
for colname in list(oxy.columns.values):
    oxy.rename(columns={colname: 'Oxy: ' + colname}, inplace=True)
oxy['Oxy: Oxygen Bottle #'] = oxy['Oxy: Case'] + oxy['Oxy: Sample ID'].apply(lambda x: str(x))
oxy.drop(columns=['Oxy: Sample ID','Oxy: Case'], inplace=True)
oxy.head()

# Merge the salinity values
log = log.merge(sal, how='left', left_on=['Log: Station-Cast #', 'Log: Salts Bottle #'], right_on=['Sal: Station','Sal: Salts Bottle #'])
# Merge the oxygen values
log = log.merge(oxy, how='left', left_on=['Log: Station-Cast #', 'Log: Oxygen Bottle #'], right_on=['Oxy: Station','Oxy: Oxygen Bottle #'])

# This block checks the merge
log[log["Log: Oxygen Bottle #"].notna()][["Log: Salts Bottle #","Sal: Salts Bottle #","Log: Oxygen Bottle #","Oxy: Oxygen Bottle #"]]

# Drop unnecessary columns
drop_columns = ['Sal: Cruise','Sal: Station','Sal: Niskin','Sal: Salts Bottle #','Oxy: Cruise','Oxy: Station','Oxy: Oxygen Bottle #','Oxy: Units']
log.drop(columns=drop_columns, inplace=True)

dupes = log.duplicated()
log[dupes]

# **If there are no oxygen or salinity data:**

# If there are now salinity or oxygen data
log["Oxy: Oxygen [mL/L]"] = log["Log: Oxygen Bottle #"]
log["Sal: Salinity [psu]"] = log["Log: Salts Bottle #"]

# **===================================================================================================================**
# ### Chlorophyll Data

chl = pd.read_excel(chl_path, sheet_name='Chl')
# Collect the subset of relevant columns 
chl = chl[["Station-Cast #","Niskin #","Filter \nSample #","Chl (ug/l)","Phaeo (ug/l)","Comments"]]
# Rename the columns to name the source
for colname in list(chl.columns.values):
    chl.rename(columns = {colname: "Chl: " + colname}, inplace=True)
# Remove the spaces from filter sample number
chl["Chl: Filter Sample #"] = chl["Chl: Filter \nSample #"].apply(lambda x: x.replace(" ",""))
chl

# Clean up the log filter sample names
log['Log: Chlorophyll Filter Sample #'] = log["Log: Chlorophyll Filter Sample #"].apply(lambda x: x.replace('-','/') if not pd.isnull(x) else x)
log[log["Log: Chlorophyll Filter Sample #"].notna()]["Log: Chlorophyll Filter Sample #"]

# Now merge the chlorophyll with the sampling log
log = log.merge(chl, how="left", left_on=["Log: Chlorophyll Filter Sample #"], right_on=["Chl: Filter \nSample #"])

for i in range(len(log)):
    a = log["Log: Chlorophyll Filter Sample #"].iloc[i]
    b = log["Chl: Filter Sample #"].iloc[i]
    if a != b:
        if pd.isnull(a) and pd.isnull(b):
            pass
        else:
            print(str(a) + ": " + str(b))

# Drop unnecessary columns
log.drop(columns=["Chl: Station-Cast #","Chl: Niskin #", "Chl: Filter Sample #"], inplace=True)
log

# **If there is no chlorophyll data yet, need to fill it in with the sample IDs**

# If there is no chlorophyll data yet, need to fill it in 
log["Chl: Chl (ug/l)"] = log["Log: Chlorophyll Filter Sample #"].apply(lambda x: x.replace('-','/') if type(x) == str else x)
log["Chl: Phaeo (ug/l)"] = log["Chl: Chl (ug/l)"]
log["Chl: Comments"] = None

# **===================================================================================================================**
# ### Nutrients

nuts = pd.read_excel(nutrients_path, sheet_name='Summary')

# Rename the columns to name the source
for colname in list(nuts.columns.values):
    nuts.rename(columns={colname: "Nuts: " + colname.replace('Avg: ','')}, inplace=True)
nuts

# Now merge the nutrients data into the sampling log data
log = log.merge(nuts, how="left", left_on=["Log: Nitrate Bottle 1"], right_on=["Nuts: Sample ID"])

# Now check that the merge worked
log[log['Log: Nitrate Bottle 1'].apply(type) != float][["Log: Nitrate Bottle 1","Nuts: Sample ID"]]

# Eliminate the extraneous columns
log.drop(columns=["Nuts: Sample ID"], inplace=True)
log.head()

# **If there is no nutrients data yet, need to fill it in with sample IDs**

nuts_columns = ['Nuts: Nitrate [µmol/L]', 'Nuts: Phosphate [µmol/L]', 'Nuts: Silicate [µmol/L]', 'Nuts: Nitrate+Nitrite [µmol/L]', 'Nuts: Ammonium [µmol/L]','Nuts: Nitrite [µmol/L]']
for col in nuts_columns:
    log[col] = log["Log: Nitrate Bottle 1"]

# **===================================================================================================================**
# ### DIC 

dic = pd.read_excel(dic_path, header=1)
dic.head()

dic['CRUISE_ID']

# Get only the DIC values for a leg of a cruise
# cruise_id = 'AR04-A'
dic = dic[dic['CRUISE_ID'] == cruise_id]
dic

# Select a subset of the columns needed
dic = dic[["CAST_NO", "NISKIN_NO", "DIC_UMOL_KG", "DIC_FLAG_W", "TA_UMOL_KG", "TA_FLAG_W", "PH_TOT_MEA", "TMP_PH_DEG_C", "PH_FLAG_W"]]
# Rename the columns to name the source
for colname in list(dic.columns.values):
    dic.rename(columns={colname: "DIC: " + colname}, inplace=True)
dic.head()

# Merge the carbon data into the sampling log
log = log.merge(dic, how="left", left_on=["Log: Station-Cast #","Log: Niskin #"], right_on=["DIC: CAST_NO", "DIC: NISKIN_NO"])
# log= log.merge(dic, how="left", left_on=["Log: DIC/TA Bottle #"], right_on=["DIC: SAMPLE_ID"])
# Check that the merge worked
# log[log['DIC: CAST_NO'].apply(np.isnan) == False][['Log: Station-Cast #', 'Log: Niskin #', 'DIC: CAST_NO', 'DIC: NISKIN_NO']]

# Drop unnecessary columns
log.drop(columns=["DIC: CAST_NO","DIC: NISKIN_NO"], inplace=True)
# log.drop(columns=["DIC: SAMPLE_ID"], inplace=True)
log.head()

# **If there is no carbon system data yet, need to fill it in with sample IDs**

dic_columns = ["DIC: CAST_NO", "DIC: NISKIN_NO", "DIC: DIC_UMOL_KG", "DIC: DIC_FLAG_W", "DIC: TA_UMOL_KG", "DIC: TA_FLAG_W", "DIC: PH_TOT_MEA", "DIC: TMP_PH_DEG_C", "DIC: PH_FLAG_W"]
for col in dic_columns:
    if 'ph' in col.lower():
        log[col] = log["Log: Ph Bottle #"]
    else:
        log[col] = log["Log: DIC/TA Bottle #"]

# **===================================================================================================================**
# ### CTD Data

# Load the CTD Data
ctd = pd.read_csv(sample_dir + 'CTD_Summary.csv')
ctd.drop(columns='Unnamed: 0', inplace=True)
# Replace the CTD w/CTD: for easier post-processing
for colname in list(ctd.columns.values):
    ctd.rename(columns={colname: 'CTD: ' + colname.replace('CTD ',"")}, inplace=True)
ctd.head()

ctd["CTD: Cast"] = ctd["CTD: Cast"].apply(lambda x: x.lstrip('0'))

# With the CTD data and the Log Data, I want to merge _only_ on the log columns, because those are the measurements we made. This is because the CTD data is more accurate in the measurements.

df = log.merge(ctd, how="outer", left_on=["Log: Station-Cast #", "Log: Niskin #"], right_on=["CTD: Cast","CTD: Bottle Position"])
df.drop_duplicates(inplace=True)
df.info()

[x for x in df.columns.values if 'duplicate' in x.lower()]

# Select a subset of the available columns which will be kept
columns = ['Log: Cruise ID',
           'Log: Station-Cast #',
           'Log: Target Station',
           'CTD: Start Latitude [degrees]', 
           'CTD: Start Longitude [degrees]',
           'CTD: Start Time [UTC]',
           'Log: Bottom Depth [m]',
           'CTD: Filename',
           'CTD: Bottle Position',
           'CTD: Date Time', 
           'CTD: Pressure, Digiquartz [db]', 
           'CTD: Depth [salt water, m]',
           'CTD: Latitude [deg]', 
           'CTD: Longitude [deg]', 
           'CTD: Temperature [ITS-90, deg C]',
           'CTD: Temperature, 2 [ITS-90, deg C]', 
           'CTD: Conductivity [S/m]', 
           'CTD: Conductivity, 2 [S/m]', 
           'CTD: Salinity, Practical [PSU]', 
           'CTD: Salinity, Practical, 2 [PSU]', 
           'CTD: Oxygen, SBE 43 [ml/l]', 
           'CTD: Oxygen Saturation, Garcia & Gordon [ml/l]', 
           'CTD: Beam Attenuation, WET Labs C-Star [1/m]',
           'CTD: Beam Transmission, WET Labs C-Star [%]', 
           'Oxy: Oxygen [mL/L]', 
           'Log: Oxygen Duplicate',
           'Chl: Chl (ug/l)', 
           'Chl: Phaeo (ug/l)', 
           'Log: Chlorophyll Duplicate', 
           'Log: Chlorophyll Filter Duplicate',
           'Nuts: Nitrate', # [µmol/L]',
           'Nuts: Phosphate',# [µmol/L]',
           'Nuts: Silicate', # [µmol/L]', 
           'Nuts: Nitrate+Nitirte',# [µmol/L]',
           'Nuts: Ammonium',# [µmol/L]', 
           'Nuts: Nitrite',# [µmol/L]', 
           'Log: Nitrate Duplicate',
           'Sal: Salinity [psu]',
           'Log: Salts Duplicate',
           'DIC: TA_UMOL_KG', 
           'DIC: TA_FLAG_W', 
           'DIC: DIC_UMOL_KG', 
           'DIC: DIC_FLAG_W',
           'DIC: PH_TOT_MEA', 
           'DIC: TMP_PH_DEG_C', 
           'DIC: PH_FLAG_W',
           'Log: Comments', 
           'Chl: Comments']

summary = df[columns]
summary = summary.sort_values(by=["Log: Station-Cast #","CTD: Bottle Position"])

summary['Log: Bottom Depth [m]'] = summary['Log: Bottom Depth [m]'].apply(lambda x: x.replace('m','').strip() if type(x) == str else x)

# Now, I need to fill in metadata columns based on other columns to make as complete a dataset as is possible
summary['Log: Station-Cast #'] = summary['Log: Station-Cast #'].fillna(value=df['CTD: Cast'])
summary['CTD: Start Latitude [degrees]'] = summary['CTD: Start Latitude [degrees]'].fillna(value=df['Log: Start Latitude'])
summary['CTD: Start Longitude [degrees]'] = summary['CTD: Start Longitude [degrees]'].fillna(value=df['Log: Start Longitude'])
summary['CTD: Start Time [UTC]'] = summary['CTD: Start Time [UTC]'].fillna(value=df['Log: Start Date'])
summary['CTD: Bottle Position'] = summary['CTD: Bottle Position'].fillna(value=df['Log: Niskin #'])

summary = summary.sort_values(by=['Log: Station-Cast #','CTD: Bottle Position'])
summary

# Create a straight-up mapping instead of this weird fuzzy-wuzzy matching
name_map = {
    'Cruise': 'Log: Cruise ID',
    'Station': 'Log: Station-Cast #',
    'Target Asset': 'Log: Target Station',
    'Start Latitude [degrees]': 'CTD: Start Latitude [degrees]',
    'Start Longitude [degrees]': 'CTD: Start Longitude [degrees]',
    'Start Time [UTC]': 'CTD: Start Time [UTC]',
    'Cast': 'Log: Station-Cast #',
    'Cast Flag': None,
    'Bottom Depth at Start Position [m]': 'Log: Bottom Depth [m]',
    'File': 'CTD: Filename',
    'File Flag': None,
    'Niskin/Bottle Position': 'CTD: Bottle Position',
    'Niskin Flag': None,
    'Bottle Closure Time [UTC]': 'CTD: Date Time',
    'Pressure [db]': 'CTD: Pressure, Digiquartz [db]',
    'Pressure Flag': None,
    'Depth [m]': 'CTD: Depth [salt water, m]',
    'Latitude [deg]': 'CTD: Latitude [deg]',
    'Longitude [deg]': 'CTD: Longitude [deg]',
    'Temperature 1 [deg C]': 'CTD: Temperature [ITS-90, deg C]',
    'Temperature 1 Flag': None,
    'Temperature 2 [deg C]': 'CTD: Temperature, 2 [ITS-90, deg C]',
    'Temperature 2 Flag': None,
    'Conductivity 1 [S/m]': 'CTD: Conductivity [S/m]',
    'Conductivity 1 Flag': None,
    'Conductivity 2 [S/m]': 'CTD: Conductivity, 2 [S/m]',
    'Conductivity 2 Flag': None,
    'Salinity 1, uncorrected [psu]': 'CTD: Salinity, Practical [PSU]',
    'Salinity 2, uncorrected [psu]': 'CTD: Salinity, Practical, 2 [PSU]',
    'Oxygen, uncorrected [mL/L]': 'CTD: Oxygen, SBE 43 [ml/l]',
    'Oxygen Flag': None,
    'Oxygen Saturation [mL/L]': 'CTD: Oxygen Saturation, Garcia & Gordon [ml/l]',
    'Fluorescence [mg/m^3]': None,
    'Fluorescence Flag': None,
    'Beam Attenuation [1/m]': 'CTD: Beam Attenuation, WET Labs C-Star [1/m]',
    'Beam Transmission [%]': 'CTD: Beam Transmission, WET Labs C-Star [%]',
    'Transmissometer Flag': None,
    'pH': None,
    'pH Flag': None,
    'Discrete Oxygen [mL/L]': 'Oxy: Oxygen [mL/L]',
    'Discrete Oxygen Flag': None,
    'Discrete Oxygen Duplicate Flag': 'Log: Oxygen Duplicate',
    'Discrete Chlorophyll [ug/L]': 'Chl: Chl (ug/l)',
    'Discrete Phaeopigment [ug/L]': 'Chl: Phaeo (ug/l)',
    'Discrete Fo/Fa Ratio': None,
    'Discrete Fluorescence Flag': None,
    'Discrete Fluorescence Duplicate Flag': 'Log: Chlorophyll Duplicate',
    'Discrete Phosphate [uM]': 'Nuts: Phosphate', #' [µmol/L]',
    'Discrete Silicate [uM]': 'Nuts: Silicate',# [µmol/L]',
    'Discrete Nitrate [uM]': 'Nuts: Nitrate',# [µmol/L]',
    'Discrete Nitrite [uM]': 'Nuts: Nitrite',# [µmol/L]',
    'Discrete Ammonium [uM]': 'Nuts: Ammonium',# [µmol/L]',
    'Discrete Nutrients Flag': None,
    'Discrete Nutrients Duplicate Flag': 'Log: Nitrate Duplicate',
    'Discrete Salinity [psu]': 'Sal: Salinity [psu]',
    'Discrete Salinity Flag': None,
    'Discrete Salinity Duplicate Flag': 'Log: Salts Duplicate',
    'Discrete Alkalinity [µmol/kg]': 'DIC: TA_UMOL_KG',
    'Discrete Alkalinity Flag': 'DIC: TA_FLAG_W',
    'Discrete DIC [µmol/kg]': 'DIC: DIC_UMOL_KG',
    'Discrete DIC Flag': 'DIC: DIC_FLAG_W',
    'Discrete pCO2 [µatm]': None, 
    'Discrete pCO2 Analysis Temp [C]': None,
    'Discrete pCO2 Flag': None,
    'Discrete pH [Total scale]': 'DIC: PH_TOT_MEA',
    'Discrete pH Analysis Temp [C]': 'DIC: TMP_PH_DEG_C',
    'Discrete pH Flag': 'DIC: PH_FLAG_W',
    'Calculated Alkalinity [µmol/kg]': None,
    'Calculated DIC [µmol/kg]': None,
    'Calculated pCO2 [µatm]': None,
    'Calculated pH': None,
    'Calculated CO2aq [µmol/kg]': None,
    'Calculated bicarb [µmol/kg]': None,
    'Calculated CO3 [µmol/kg]': None,
    'Calculated Omega-C': None,
    'Calculated Omega-A': None,
    'Comments': 'Log: Comments',
    'Chl Comments': 'Chl: Comments'
}

final = pd.DataFrame()
for key in name_map:
    column = name_map.get(key)
    if column is not None:
        final[key] = summary[column]
    else:
        final[key] = None

final.sort_values(by=['Cruise','Station','Niskin/Bottle Position'], inplace=True)

final

final.drop_duplicates(inplace=True)
final

cruise_id

# cruise_id = 'AR-31A'
final['Cruise'] = final['Cruise'].fillna(value=cruise_id)

cruise_name = cruise.replace('/','').split('_')[0]
current_date = pd.to_datetime(pd.datetime.now()).tz_localize(tz='US/Eastern').tz_convert(tz='UTC')
version = '1-2'

cruise_id, cruise_name

filename = '_'.join([cruise_name,cruise_id,'Discrete','Summary',current_date.strftime('%Y-%m-%d'),'ver',version,'.csv'])
filename

final.fillna(value=-9999999,inplace=True)

final.to_csv(basepath+array+cruise+filename, index=False)



# ## Update summary sheets
#

basepath = '/home/andrew/Documents/OOI-CGSN/QAQC_Sandbox/Ship_data/'

os.listdir(basepath+'Pioneer')

basepath = '/home/andrew/Documents/OOI-CGSN/QAQC_Sandbox/Ship_data/'
array = 'Pioneer/'
cruise =   'Pioneer-08_AR-18_2017-05-30/'

sorted(os.listdir(basepath+array+cruise))

water = 'Water Sampling/'
ctd = 'ctd/'
leg = 'Leg 1 (ar08a)/'

sorted(os.listdir(basepath + array + cruise + water))

sample_dir = basepath + array + cruise + ctd
water_dir = basepath + array + cruise + water
log_path = water_dir + 'Pioneer-08_AR-18A_CTD_Sampling_Log.xlsx'
chl_path = water_dir + ''
nutrients_path = water_dir + 'Pioneer-08_AR-18_DIC_Sample_Data_2019-11-06_ver_1-00.xlsx'
salts_and_o2_path = water_dir + 'Pioneer-08_AR-18A_Oxygen_Salinity_Sample_Data/'


data_path = basepath + array + cruise + 'Pioneer-08_AR-18_Discrete_Summary_2019-11-04_ver_1-02_.csv'

data = pd.read_csv(data_path)
data

data.columns

# Load the relevant data
dic_path = basepath + array + cruise + water + 'Pioneer-08_AR-18_DIC_Sample_Data_2019-11-06_ver_1-00.xlsx'
dic = pd.read_excel(dic_path)
dic.head()


def reformat_cruise_id(x):
    if '-A' in x:
        x = 'AR-18A'
    elif '-B' in x:
        x = 'AR-18B'
    elif '-C' in x:
        x = 'AR-18C'
    else:
        x
    return x


dic["CRUISE_ID"] = dic["CRUISE_ID"].apply(lambda x: reformat_cruise_id(x) )

df = data.merge(dic, how='left', left_on=['Cruise', 'Station', 'Niskin/Bottle Position'], right_on = ["CRUISE_ID", "CAST_NO", "NISKIN_NO"])

df["Discrete DIC [µmol/kg]"] = df["DIC_UMOL_KG"]
df["Discrete DIC Flag"] = df['DIC_FLAG_W']
df["Discrete Alkalinity [µmol/kg]"] = df["TA_UMOL_KG"]
df["Discrete Alkalinity Flag"] = df['TA_FLAG_W']
df["Discrete pH [Total scale]"] = df['PH_TOT_MEA']
df["Discrete pH Analysis Temp [C]"] = df["TMP_PH_DEG_C"]
df["Discrete pH Flag"] = df["PH_FLAG_W"]

df[df["Discrete pH [Total scale]"].notna()]["Discrete pH [Total scale]"]

df.drop(columns=[x for x in dic.columns], inplace=True)

df.columns

df.fillna(value=-9999999,inplace=True)


def fill_flags(x):
    if x == -9999999 or x == '-9999999':
        return x
    elif str(x).lower() == 'false':
        return x
    elif str(x).lower() == 'true':
        return x
    else:
        return str(x).zfill(16)


for column in df.columns:
    if 'flag' in column.lower():
        df[column] = df[column].apply(lambda x: fill_flags(x))

df

df.to_csv(basepath+array+cruise+'Pioneer-08_AR-18_Discrete_Summary_2019-11-07_ver_1-03_.csv', index=False)

data


