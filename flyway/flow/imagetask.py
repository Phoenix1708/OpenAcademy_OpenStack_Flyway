# -*- coding: utf-8 -*-

#    Copyright (C) 2012 eBay, Inc. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from taskflow import task
import keystoneclient.v2_0.client as ksclient
from glanceclient import Client

from common import config as cfg


LOG = logging.getLogger(__name__)


class ImageMigrationTask(task.Task):
    """
    Task to migrate all user info from the source cloud to the target cloud.
    """

    def execute(self):
        LOG.info('Migrating all users ...')
	
	#Connect to source cloud keystone
	ks_source = ksclient.Client(username=cfg.CONF.SOURCE.os_username,
                                    password=cfg.CONF.SOURCE.os_password,
                                    auth_url=cfg.CONF.SOURCE.os_auth_url,
                                    tenant_name=cfg.CONF.SOURCE.os_tenant_name)
	
	source_auth_token = ks_source.auth_ref['token']['id']
	source_tenant_id = ks_source.auth_ref['token']['tenant']['id']
	print 'source_token: ',source_auth_token
	print 'source_tenant_id:',source_tenant_id

	#Connect to target cloud keystone
	ks_target = ksclient.Client(username=cfg.CONF.TARGET.os_username,
                                    password=cfg.CONF.TARGET.os_password,
                                    auth_url=cfg.CONF.TARGET.os_auth_url,
                                    tenant_name=cfg.CONF.TARGET.os_tenant_name)
		
	target_auth_token = ks_target.auth_ref['token']['id']
	target_tenant_id = ks_target.auth_ref['token']['tenant']['id']
	print 'target_token: ',target_auth_token
	print 'target_tenant_id:',target_tenant_id
	
	#Connect to source cloud glance
	gl_source = Client('1',
			   endpoint=cfg.CONF.SOURCE.os_endpoint,
		           token=source_auth_token)
	
	#Connect to target cloud glance
	gl_target = Client('1', 
			   endpoint=cfg.CONF.TARGET.os_endpoint, 
			   token=target_auth_token)
	target_imageNames = []
	for image in gl_target.images.list():
		target_imageNames.append(image.name)
	print target_imageNames

	#Migrate source images that doe not exist in target cloud
	source_imagesDir = '/opt/stack/data/glance/images/'
	
	for source_image in gl_source.images.list():
		if source_image.name not in target_imageNames:
			image = gl_target.images.create(name=source_image.name,
			        			disk_format='qcow2',
			        			container_format='bare',
			        			is_public='True',
			        			data=open(source_imagesDir+source_image.id,'rb'))
			print 'ImageMigration is done!'
			print 'ImageStatus: ' + source_image.name + ' is ' + source_image.status
	"""
        for user in ks_source.users.list():
            LOG.debug(user)
            # TODO: use ks_target to create the user info in the target cloud
	"""