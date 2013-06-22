from datetime import datetime
from dateutil import parser
import urlparse
import boto

from triv.io import datasources

class S3Source(datasources.DataSource):
  """Treats S3 like a database"""
    
  def __init__(self, parsed_url):

    super(S3Source,self).__init__(parsed_url)

    username = parsed_url.username if parsed_url.username else ''
    password = parsed_url.password if parsed_url.password else ''


    self.access_key_id     = urlparse.unquote(username)
    self.secret_access_key = urlparse.unquote(password)

    if self.access_key_id and self.secret_access_key:
      self.conn = boto.connect_s3(self.access_key_id , self.secret_access_key)
    else:
      # as of boto 2.9.6 if access_key & and secret are None
      # then s3 attempts to determine them.
      self.conn = boto.connect_s3('','',anon=True)

    self.bucket_name = parsed_url.hostname
    self.bucket = self.conn.get_bucket(self.bucket_name,validate=False)

  
  def generate_url(self, key, seconds_good_for=60*60*24, force_http=False):
    if not self.conn.anon:
      return key.generate_url(seconds_good_for, force_http=force_http)
    else:
      protocol = 'http' if force_http else 'https'
      return self.conn.calling_format.build_url_base(
        self.conn, 
        protocol,
        self.conn.server_name(self.conn.port),
        key.bucket.name, key.key
      )

      



  def earliest_record_time(self):
    # Grab and parse the first key
    #self.bucket.get_all_keys(self.prefix + '/', delimiter='/', max_keys=1)
    for key in self.bucket.get_all_keys(prefix=self.prefix + '/', delimiter='/', max_keys=1):
      parts = filter(None, key.name.split('/')[1:])
      params = dict([entry.split('=',1) for entry in parts])
      date = params['dt']
      return parser.parse(date)
    
    # if bucket is empty return now
    return datetime.utcnow()

  def segment_between(self, start, end):
    # TODO: this won't return a range of key's only the bucket that start's exactly
    # with the start time
    keys = self.bucket.list("{0}/dt={1}/".format(self.prefix, start.isoformat()), delimiter='/')
    seconds_good_for = 60*60*24
    urls = [self.generate_url(k,force_http=True) for k in keys if k.size > 0]
    return urls

    
datasources.set_source_for_scheme(S3Source,'s3')