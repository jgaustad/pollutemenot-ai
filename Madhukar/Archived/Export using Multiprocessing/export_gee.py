
START_DATE = '2018-08-01'
END_DATE = '2020-04-01'
CLOUD_FILTER = 60
CLD_PRB_THRESH = 40
NIR_DRK_THRESH = 0.15
CLD_PRJ_DIST = 2
BUFFER = 100
BUCKET = 'pollutemenot-ai'
# FOLDER = "test_final6"
# FOLDER = 'MR_GEE_images_final2'
FOLDER = "GEE_images_final2"


import ee
ee.Initialize()

# # Build a Sentinel-2 collection
# # Sentinel-2 surface reflectance and Sentinel-2 cloud probability are two
# different image collections. Each collection must be filtered similarly
# (e.g., by date and bounds) and then the two filtered collections must
# be joined.

# # Define a function to filter the SR and s2cloudless collections according
# to area of interest and date parameters, then join them on the system:index
# property. The result is a copy of the SR collection where each image has a
# new 's2cloudless' property whose value is the corresponding s2cloudless image.

def get_s2_sr_cld_col(aoi, start_date, end_date):
    # import ee
    # ee.Initialize()

    # Import and filter S2 SR.
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    # Import and filter s2cloudless.
    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
        .filterBounds(aoi)
        .filterDate(start_date, end_date))

    # Join the filtered s2cloudless collection to the SR collection by
    # the 'system:index' property.
    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))


# In[6]:


def add_cloud_bands(img):
    # import ee
    # ee.Initialize()

    # Get s2cloudless image, subset the probability band.
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')

    # Condition s2cloudless by the probability threshold value.
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')

    # Add the cloud probability layer and cloud mask as image bands.
    return img.addBands(ee.Image([cld_prb, is_cloud]))


# In[7]:


def add_shadow_bands(img):
    # import ee
    # ee.Initialize()

    # Identify water pixels from the SCL band.
    not_water = img.select('SCL').neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))


# In[8]:


def add_cld_shdw_mask(img):
    # Add cloud component bands.
    img_cloud = add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw.focal_min(2).focal_max(BUFFER*2/20)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
        .rename('cloudmask'))

    # Add the final cloud-shadow mask to the image.
    return img_cloud_shadow.addBands(is_cld_shdw)


# In[9]:


def apply_cld_shdw_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)


# In[10]:


def s2_sr_median_func(lat, lon, buffer_m):
  import ee
  ee.Initialize()
  AOI = ee.Geometry.Point([lon, lat])#.buffer(res).bounds()
  s2_sr_cld_col = get_s2_sr_cld_col(AOI, START_DATE, END_DATE)
  s2_sr_median = (s2_sr_cld_col.map(add_cld_shdw_mask)
                             .map(apply_cld_shdw_mask)
                             .median())
  return s2_sr_median



# # Set up bounding box

# In[11]:


def square(lat, lon, size):
  crs_proj = "EPSG:4326"
  return ee.Geometry.Point([lon, lat], proj=crs_proj).buffer(size).bounds()





def make_ndvi(image, red='B4', nir='B8'):
  return image.normalizedDifference([nir, red])

def make_ndwi(image, green='B3', nir='B8'):
  return image.normalizedDifference([green, nir])


def make_mndvi(image, red='B4', nir='B8'):
  nir = image.select('B8')
  red = image.select('B4')
  aerosols = image.select('B1')
  mndvi = (nir.subtract(red)
                      .divide(
                          nir.add(red)
                          .subtract(aerosols.add(aerosols))
                          )
                      .rename('mndvi'))
  return mndvi

def make_mndwi(image, green='B3', swir='B11'):
  green = image.select('B3')
  swir = image.select('B11')
  mndwi = (green.subtract(swir)
                .divide(
                    green.add(swir))
                .rename('mndwi'))
  return mndwi


# In[16]:


# choose median of mndwi image collection
def make_med_mndwi(lat, lon, buffer_m):
  AOI = ee.Geometry.Point([lon, lat])#.buffer(res).bounds()
  s2_sr_cld_col = get_s2_sr_cld_col(AOI, START_DATE, END_DATE)
  med_mndwi = (s2_sr_cld_col.map(add_cld_shdw_mask)
                             .map(apply_cld_shdw_mask)
                             .map(make_mndwi)
                             .median()
                             )
  return med_mndwi # returns the image with median mndwi in the date range



# In[17]:


# choose the max water pixel from mndwi image collection
def s2_sr_greenestpixel_func2(lat, lon, buffer_m):
  AOI = ee.Geometry.Point([lon, lat])#.buffer(res).bounds()
  s2_sr_cld_col = get_s2_sr_cld_col(AOI, START_DATE, END_DATE)
  s2_sr_greenestpixel = (s2_sr_cld_col.map(add_cld_shdw_mask)
                             .map(apply_cld_shdw_mask)
                             .map(make_mndwi)
                             .qualityMosaic('mndwi')
                             )
  # returns the image with highest mndwi in the date range
  return s2_sr_greenestpixel






import pandas as pd
# datapath = "drive/MyDrive/Data/combined_v2.csv"
datapath = "combined_regular_clean_with_ssurgo_variables.csv"
df = pd.read_csv(datapath, encoding = "ISO-8859-1")

# column name 'index' is conflicting with the native index of dataframe
# hence, creating a new column named "Index"
df["Index"] = df.index + 1


# # Exporting Functions
#

# In[21]:


def doExport_RBG2(lat, lon, index_danum, band, size=1000):
  image = s2_sr_median_func(lat, lon, size)
  image = image.select('B4', 'B3', 'B2', 'B8')
  imageRGB = image.visualize(**{'bands': ['B4', 'B3', 'B2'], 'max': 9000, 'min': 0.5})

  if size == 1000:
    size_ = "hires"
  else:
    size_ = 'lores'
  folder = FOLDER

  task = ee.batch.Export.image.toCloudStorage(
      image = imageRGB,
      description = index_danum,
      bucket = BUCKET,
      # fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum  + band + size_,
      fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum + '_' + band + '_' + size_,
      region = square(lat, lon, size).getInfo().get('coordinates'),
      crs = 'EPSG:4326',
      # crs_transform = crs_transform,
      dimensions = "256x256",
      maxPixels = 1E13,
      fileFormat = "GeoTIFF",
      formatOptions = {
      "cloudOptimized" : True
      }
      )
  task.start()
    # Block until the task completes.
  # print('Running image export to Cloud Storage...')
  import time
  while task.active():
    time.sleep(30)


# In[22]:


def doExport_index2(lat, lon, index_danum, band, size=1000, func=make_ndvi):
  image = s2_sr_median_func(lat, lon, size)
  # image = image.select('B4', 'B3', 'B2', 'B8')

  if size == 1000:
    size_ = "hires"
  elif size == 10000:
    size_ = 'lores'
  folder = FOLDER

  task = ee.batch.Export.image.toCloudStorage(
      image = func(image),
      description = index_danum + '_' + size_,
      bucket = BUCKET,
      # fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum  + band + size_,
      fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum + '_' + band + '_' + size_,
      region = square(lat, lon, size).getInfo().get('coordinates'),
      crs = 'EPSG:4326',
      # crs_transform = crs_transform,
      dimensions = "256x256",
      maxPixels = 1E13,
      fileFormat = "GeoTIFF",
      formatOptions = {
      "cloudOptimized" : True
      }
      )
  task.start()
    # Block until the task completes.
  # print('Running image export to Cloud Storage...')
  import time
  while task.active():
    time.sleep(30)


# In[23]:


def doExport_mmndwi(lat, lon, index_danum, band="gmndwi", size=1000, func=None):
  image = make_med_mndwi(lat, lon, size)
  # image = image.select('B4', 'B3', 'B2', 'B8')

  if size == 1000:
    size_ = "hires"
  elif size == 10000:
    size_ = 'lores'
  folder = FOLDER

  task = ee.batch.Export.image.toCloudStorage(
      image = image,
      description = index_danum + '_' + size_,
      bucket = BUCKET,
      # fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum  + band + size_,
      fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum + '_' + band + '_' + size_,
      region = square(lat, lon, size).getInfo().get('coordinates'),
      crs = 'EPSG:4326',
      # crs_transform = crs_transform,
      dimensions = "256x256",
      maxPixels = 1E13,
      fileFormat = "GeoTIFF",
      formatOptions = {
      "cloudOptimized" : True
      }
      )
  task.start()
    # Block until the task completes.
  # print('Running image export to Cloud Storage...')
  import time
  while task.active():
    time.sleep(30)


# In[24]:


def doExport_gmndwi(lat, lon, index_danum, band="gmndwi", size=1000, func=None):
  image = s2_sr_greenestpixel_func2(lat, lon, size)
  # image = image.select('B4', 'B3', 'B2', 'B8')

  if size == 1000:
    size_ = "hires"
  elif size == 10000:
    size_ = 'lores'
  folder = FOLDER

  task = ee.batch.Export.image.toCloudStorage(
      image = image,
      description = index_danum + '_' + size_,
      bucket = BUCKET,
      # fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum  + band + size_,
      fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum + '_' + band + '_' + size_,
      region = square(lat, lon, size).getInfo().get('coordinates'),
      crs = 'EPSG:4326',
      # crs_transform = crs_transform,
      dimensions = "256x256",
      maxPixels = 1E13,
      fileFormat = "GeoTIFF",
      formatOptions = {
      "cloudOptimized" : True
      }
      )
  task.start()
    # Block until the task completes.
  # print('Running image export to Cloud Storage...')
  import time
  while task.active():
    time.sleep(30)


# In[25]:


def doExport_srtm2(lat, lon, index_danum, band, size=1000, func=None):
  # print("inside doExport_srtm2 before import ee")
  # import ee
  # ee.Initialize()
  # print("inside doExport_srtm2 after ee.Initialize")
  image = ee.Image('USGS/SRTMGL1_003')
  # image = ee.Terrain.slope(srtm)
  if size == 1000:
    size_ = "hires"
  elif size == 10000:
    size_ = 'lores'
  folder = FOLDER

  task = ee.batch.Export.image.toCloudStorage(
      image = image,
      description = index_danum + '_' + size_,
      bucket = BUCKET,
      # fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum  + band + size_,
      fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum + '_' + band + '_' + size_,
      region = square(lat, lon, size).getInfo().get('coordinates'),
      crs = 'EPSG:4326',
      # crs_transform = crs_transform,
      dimensions = "256x256",
      maxPixels = 1E13,
      fileFormat = "GeoTIFF",
      formatOptions = {
      "cloudOptimized" : True
      }
      )
  task.start()
  # print(task.start())
    # Block until the task completes.
  # print('Running image export to Cloud Storage...')
  import time
  while task.active():
    time.sleep(30)


# In[26]:


def doExport_slope2(lat, lon, index_danum, band, size=1000, func=None):
  srtm = ee.Image('USGS/SRTMGL1_003')
  image = ee.Terrain.slope(srtm)
  if size == 1000:
    size_ = "hires"
  elif size == 10000:
    size_ = 'lores'
  folder = FOLDER

  task = ee.batch.Export.image.toCloudStorage(
      image = image,
      description = index_danum + '_' + size_,
      bucket = BUCKET,
      # fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum  + band + size_,
      fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum + '_' + band + '_' + size_,
      region = square(lat, lon, size).getInfo().get('coordinates'),
      crs = 'EPSG:4326',
      # crs_transform = crs_transform,
      dimensions = "256x256",
      maxPixels = 1E13,
      fileFormat = "GeoTIFF",
      formatOptions = {
      "cloudOptimized" : True
      }
      )
  task.start()
    # Block until the task completes.
  # print('Running image export to Cloud Storage...')
  import time
  while task.active():
    time.sleep(30)




def doExport_jrc2(lat, lon, index_danum, band, size=1000, func=None, res='hires'):
  jrc = ee.Image("JRC/GSW1_2/GlobalSurfaceWater")
  # jrc_bands = jrc.select("seasonality", "transition", "max_extent")\
                # .bandNames().getInfo()
  if band == "transition":
    jrc = jrc.select("transition")
  elif band == "max_extent":
    jrc = jrc.select("max_extent")
  else:
    jrc = jrc.select("seasonality")

  if size == 1000:
    size_ = "hires"
  elif size == 10000:
    size_ = 'lores'
  folder = FOLDER

  task = ee.batch.Export.image.toCloudStorage(
      image = jrc,
      description = index_danum + '_' + size_,
      bucket = BUCKET,
      # fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum  + band + size_,
      fileNamePrefix = folder + '/' + size_ + '/' + band + '/' + index_danum + '_' + band + '_' + size_,
      region = square(lat, lon, size).getInfo().get('coordinates'),
      crs = 'EPSG:4326',
      # crs_transform = crs_transform,
      dimensions = "256x256",
      maxPixels = 1E13,
      fileFormat = "GeoTIFF",
      formatOptions = {
      "cloudOptimized" : True
      }
      )
  task.start()
    # Block until the task completes.
  # print('Running image export to Cloud Storage...')
  import time
  while task.active():
    time.sleep(30)


# In[30]:


import numpy as np
#
def export_data2(index_danum, lat, lon):
  # print("whoohoo")
  # print("hello, am in export function in", __name__)
  # print(FOLDER)
  for size in [1000, 10000]:
    # doExport_RBG2(lat, lon, index_danum, 'RBG', size)
    # doExport_index2(lat, lon, index_danum, 'ndvi', size, make_ndvi)
    # doExport_index2(lat, lon, index_danum, 'ndwi', size, make_ndwi)
    # # doExport_gmndwi(lat, lon, index_danum, 'mmndwi', size, None)

    # doExport_slope2(lat, lon, index_danum, 'slope', size, None)
    doExport_srtm2(lat, lon, index_danum, 'srtm', size, None) # this
    if size == 1000:
      doExport_jrc2(lat, lon, index_danum, 'seasonality', size, None) # this
      doExport_jrc2(lat, lon, index_danum, 'transition', size, None) # this
  for size in [1000, 10000]:
    doExport_index2(lat, lon, index_danum, 'mndvi', size, make_mndvi) # this
    doExport_index2(lat, lon, index_danum, 'mndwi', size, make_mndwi) # this
    doExport_gmndwi(lat, lon, index_danum, 'gmndwi', size, None) # this

    # doExport_jrc2(lat, lon, index_danum, 'max_extent', size, None, hires)


# # Set up global variables for Export/Import

# In[31]:
import sys


# from multiprocessing import Pool
# # from export_data_pooler import export_data_pooler
def export_data_pooler(x):
    # print("inside export_data_pooler function in", __name__)

    index, da_number, latitude, longitude = x
    # print('starting processing and uploading of index', index)
    # sys.stdout.write('starting processing and uploading of index' + str(index))
    # sys.stdout.flush()
    export_data2(str(index) + '_' + da_number, latitude, longitude)
    # print("Done uploading hires and lores of index =", index)
    # sys.stdout.write("Done uploading hires and lores of index" + str(index))
    # sys.stdout.flush()
    return index
#     df = pd.read_csv('export_log.csv')
    # df.iloc[index - 1] = "exported"
    # df.to_csv('export_log.csv')



# In[ ]:
