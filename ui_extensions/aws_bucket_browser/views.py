from django.shortcuts import render

from extensions.views import tab_extension, TabExtensionDelegate
from resources.models import Resource


class S3BucketBrowserTabDelegate(TabExtensionDelegate):
    def should_display(self):
        if self.instance.resource_type.name == 'storage':
            # TODO: further narrow this down to only show on S3 Buckets
            return True
        else:
            return False


@tab_extension(model=Resource, title="File Browser", 
               description="Browse the contents of the bucket",
               delegate=S3BucketBrowserTabDelegate)
def s3_bucket_browser(request, obj_id):
    return render(request, 'aws_bucket_browser/templates/bucket_browser.html', dict())
