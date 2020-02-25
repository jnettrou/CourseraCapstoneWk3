#!/usr/bin/env python
# coding: utf-8

# # Creating df_toronto dataframe from website

# #### Importing table from Wikipedia and converting to DF

# In[27]:


import pandas as pd


# In[28]:


df = pd.read_html('https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M')


# In[29]:


type(df)


# In[30]:


len(df)


# In[31]:


df_tor = df[0]


# In[32]:


df_tor.head(10)


# #### Fixing row 9 as stated in instructions

# In[33]:


df_tor.iloc[9,2] = "Queen's Park"
df_tor.head(10)


# #### Verifying no other rows have Neighbourhood of Not Assigned with an assigned Borough

# In[34]:


df_not = df_tor[df_tor['Neighbourhood'].str.contains("Not assigned")]
df_not


# In[35]:


df_notnot = df_not[~df_not['Borough'].str.contains("Not assigned")]
df_notnot


# #### Cleaning up dataframe by removing 'Not Assigned' Boroughs and 

# In[36]:


df_tor.describe


# In[37]:


df_tor.shape


# In[39]:


df_tor2 = df_tor[df_tor.Borough != 'Not assigned']
df_tor2.shape


# In[40]:


df_tor2.head(10)


# #### Grouping Neighbourhoods into unique Poscode/Borough combinations

# In[41]:


df_toronto = df_tor2.groupby(['Postcode','Borough'], as_index = False).agg({'Neighbourhood': ', '.join})


# In[42]:


print(df_toronto.shape)
df_toronto


# #### Importing Lat/Long file

# In[45]:


df_latlong = pd.read_csv('http://cocl.us/Geospatial_data')
df_latlong.head(15)


# #### Merging Lat/Long to Toronto DF and removing extra column

# In[46]:


df_torlatlong = df_toronto.merge(df_latlong, left_on='Postcode', right_on='Postal Code')
df_torlatlong.head()


# In[47]:


df_torlatlong.drop('Postal Code', inplace=True,axis=1)
df_torlatlong


# #### Importing Mapping libraries

# In[48]:


import numpy as np
import json
from pandas.io.json import json_normalize
import requests
import matplotlib.cm as cm
import matplotlib.colors as colors
from sklearn.cluster import KMeans
get_ipython().system('pip install folium')
import folium


# In[49]:


get_ipython().system('pip install geopy')
from geopy.geocoders import Nominatim


# #### Creating 1st Map of Toronto

# In[50]:


address = 'Toronto, ON'

geolocator = Nominatim(user_agent="tor_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude


# In[51]:


map_toronto = folium.Map(location=[latitude, longitude], zoom_start=10)
neighborhoods = df_torlatlong

for lat, lng, borough, neighborhood in zip(neighborhoods['Latitude'], neighborhoods['Longitude'], neighborhoods['Borough'], neighborhoods['Neighbourhood']):
    label = '{}, {}'.format(neighborhood, borough)
    label = folium.Popup(label, parse_html=True)
    folium.CircleMarker(
        [lat, lng],
        radius=5,
        popup=label,
        color='blue',
        fill=True,
        fill_color='#3186cc',
        fill_opacity=0.7,
        parse_html=False).add_to(map_toronto)  
    
map_toronto


# #### Gathering data from Foursquare

# In[53]:


CLIENT_ID = 'LB5FZYMLW3EKO3GDPLQICJPHT0PIM10TTYKM2CI15JANYHV0'
CLIENT_SECRET = '420ZCLLR3JDPD1DMUTGW0NSCSXRLY53BVEKAGMOXTIHXD0SG'
VERSION = '20180605'
ACCESS_TOKEN = 'AUIVBHZLCFHI1JJ0FTHVF24F1QR2MLTHKAFOT5SM1LADDINK'


# In[68]:


def getNearbyVenues(names, latitudes, longitudes, radius=500, LIMIT=100):
    
    venues_list=[]
    for name, lat, lng in zip(names, latitudes, longitudes):
        print(name)
            
        # create the API request URL
        url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
            CLIENT_ID, 
            CLIENT_SECRET, 
            VERSION, 
            lat, 
            lng, 
            radius, 
            LIMIT)
            
        # make the GET request
        results = requests.get(url).json()["response"]['groups'][0]['items']
        
        # return only relevant information for each nearby venue
        venues_list.append([(
            name, 
            lat, 
            lng, 
            v['venue']['name'], 
            v['venue']['location']['lat'], 
            v['venue']['location']['lng'],  
            v['venue']['categories'][0]['name']) for v in results])

    nearby_venues = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
    nearby_venues.columns = ['Neighborhood', 
                  'Neighborhood Latitude', 
                  'Neighborhood Longitude', 
                  'Venue', 
                  'Venue Latitude', 
                  'Venue Longitude', 
                  'Venue Category']
    
    return(nearby_venues)


# In[72]:


toronto_venues = getNearbyVenues(names=df_torlatlong['Borough'],
                                   latitudes=df_torlatlong['Latitude'],
                                   longitudes=df_torlatlong['Longitude']
                                  )


# In[94]:


toronto_venues.head()


# In[95]:


toronto_venues.groupby('Neighborhood').count()


# In[84]:


print('There are {} uniques categories.'.format(len(toronto_venues['Venue Category'].unique())))


# #### Grouping data by neighborhood

# In[98]:


# one hot encoding
toronto_onehot = pd.get_dummies(toronto_venues[['Venue Category']], prefix="", prefix_sep="")

# add neighborhood column back to dataframe
toronto_onehot['Neighborhood'] = toronto_venues['Neighborhood'] 

# move neighborhood column to the first column
fixed_columns = [toronto_onehot.columns[-1]] + list(toronto_onehot.columns[:-1])
toronto_onehot = toronto_onehot[fixed_columns]

toronto_onehot.set_index('Neighborhood', inplace=True)
toronto_onehot.head()


# In[99]:


toronto_onehot.shape


# In[100]:


toronto_grouped = toronto_onehot.groupby('Neighborhood').mean().reset_index()
toronto_grouped


# #### Identify most common venues

# In[114]:


def return_most_common_venues(row, num_top_venues):
    row_categories = row.iloc[1:]
    row_categories_sorted = row_categories.sort_values(ascending=False)
    
    return row_categories_sorted.index.values[0:num_top_venues]

num_top_venues = 10

indicators = ['st', 'nd', 'rd']

# create columns according to number of top venues
columns = ['Neighborhood']
for ind in np.arange(num_top_venues):
    try:
        columns.append('{}{} Most Common Venue'.format(ind+1, indicators[ind]))
    except:
        columns.append('{}th Most Common Venue'.format(ind+1))

# create a new dataframe
neighborhoods_venues_sorted = pd.DataFrame(columns=columns)
neighborhoods_venues_sorted['Neighborhood'] = toronto_grouped['Neighborhood']

for ind in np.arange(toronto_grouped.shape[0]):
    neighborhoods_venues_sorted.iloc[ind, 1:] = return_most_common_venues(toronto_grouped.iloc[ind, :], num_top_venues)

neighborhoods_venues_sorted.head()


# #### Cluster Neighborhoods

# In[115]:


# set number of clusters
kclusters = 5

toronto_grouped_clustering = toronto_grouped.drop('Neighborhood', 1)

# run k-means clustering
kmeans = KMeans(n_clusters=kclusters, random_state=0).fit(toronto_grouped_clustering)

# check cluster labels generated for each row in the dataframe
kmeans.labels_[0:10] 


# In[116]:


# add clustering labels
neighborhoods_venues_sorted.insert(0, 'Cluster Labels', kmeans.labels_)

toronto_merged = df_torlatlong

# merge toronto_grouped with toronto_data to add latitude/longitude for each neighborhood
toronto_merged = toronto_merged.join(neighborhoods_venues_sorted.set_index('Neighborhood'), on='Borough')

toronto_merged.head() # check the last columns!


# Had to eliminate an unmatched row, and convert the Cluster Labels to Integers -- they were floats and it was causing issues in the mapping process

# In[123]:


toronto_merged.shape
toronto_merged.dropna(inplace=True)


# In[127]:


toronto_merged['Cluster Labels'] = toronto_merged['Cluster Labels'].astype(int)


# In[128]:


toronto_merged


# #### Creating cluster map of Boroughs

# In[129]:


# create map
map_clusters = folium.Map(location=[latitude, longitude], zoom_start=11)

# set color scheme for the clusters
x = np.arange(kclusters)
ys = [i + x + (i*x)**2 for i in range(kclusters)]
colors_array = cm.rainbow(np.linspace(0, 1, len(ys)))
rainbow = [colors.rgb2hex(i) for i in colors_array]

# add markers to the map
markers_colors = []
for lat, lon, poi, cluster in zip(toronto_merged['Latitude'], toronto_merged['Longitude'], toronto_merged['Borough'], toronto_merged['Cluster Labels']):
    label = folium.Popup(str(poi) + ' Cluster ' + str(cluster), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[cluster-1],
        fill=True,
        fill_color=rainbow[cluster-1],
        fill_opacity=0.7).add_to(map_clusters)
       
map_clusters


# In[ ]:




