#!/usr/bin/env python
# (c) Copyright [2015] Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import setuptools

# In python < 2.7.4, a lazy loading of package `pbr` will break
# setuptools if some other modules registered functions in `atexit`.
# solution from: http://bugs.python.org/issue15881#msg170215
try:
    import multiprocessing  # noqa
except ImportError:
    pass

setuptools.setup(
    name='horizon_ssmc_link',
    packages=['horizon_ssmc_link'],
    version='1.0.0',
    description='Links Horizon volumes to HP 3PAR SSMC',
    long_description='Allows OpenStack users to link from a volume '
                     'displayed in Horizon to its corresponding detail '
                     'page in HP 3PAR SSMC',
    author='HP Storage Cloud Team',
    author_email='richard.hagarty@hp.com',
    url='https://github.com/hp-storage/horizon-ssmc-link',
    keywords=['openstack', 'horizon', 'horizon-plug-in', 'ssmc'],
    license='Apache',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: OpenStack',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    install_requires=[],
    setup_requires=['pbr'],
    pbr=True
)
