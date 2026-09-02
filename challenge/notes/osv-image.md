

Container Scanning Result (Debian GNU/Linux 13 (trixie)) (Based on "python" image):
Total 24 packages affected by 81 known vulnerabilities (6 Critical, 24 High, 41 Medium, 6 Low, 4 Unknown) from 2 ecosystems.
28 vulnerabilities can be fixed.


PyPI
+---------------------------------------------------------------------------------------------+
| Source:artifact:/usr/local/lib/python3.11/ensurepip/_bundled/pip-24.0-py3-none-any.whl      |
+---------+-------------------+---------------+------------+------------------+---------------+
| PACKAGE | INSTALLED VERSION | FIX AVAILABLE | VULN COUNT | INTRODUCED LAYER | IN BASE IMAGE |
+---------+-------------------+---------------+------------+------------------+---------------+
| pip     | 24.0              | Fix Available |          6 | # 7 Layer        | python        |
+---------+-------------------+---------------+------------+------------------+---------------+
+---------------------------------------------------------------------------------------------+
| Source:artifact:/usr/local/lib/python3.11/site-packages/pip-24.0.dist-info/METADATA         |
+---------+-------------------+---------------+------------+------------------+---------------+
| PACKAGE | INSTALLED VERSION | FIX AVAILABLE | VULN COUNT | INTRODUCED LAYER | IN BASE IMAGE |
+---------+-------------------+---------------+------------+------------------+---------------+
| pip     | 24.0              | Fix Available |          6 | # 7 Layer        | python        |
+---------+-------------------+---------------+------------+------------------+---------------+
+---------------------------------------------------------------------------------------------+
| Source:artifact:/usr/local/lib/python3.11/site-packages/pyjwt-2.12.0.dist-info/METADATA     |
+---------+-------------------+---------------+------------+------------------+---------------+
| PACKAGE | INSTALLED VERSION | FIX AVAILABLE | VULN COUNT | INTRODUCED LAYER | IN BASE IMAGE |
+---------+-------------------+---------------+------------+------------------+---------------+
| pyjwt   | 2.12.0            | Fix Available |          5 | # 14 Layer       | --            |
+---------+-------------------+---------------+------------+------------------+---------------+
+----------------------------------------------------------------------------------------------+
| Source:artifact:/usr/local/lib/python3.11/site-packages/requests-2.31.0.dist-info/METADATA   |
+----------+-------------------+---------------+------------+------------------+---------------+
| PACKAGE  | INSTALLED VERSION | FIX AVAILABLE | VULN COUNT | INTRODUCED LAYER | IN BASE IMAGE |
+----------+-------------------+---------------+------------+------------------+---------------+
| requests | 2.31.0            | Fix Available |          3 | # 14 Layer       | --            |
+----------+-------------------+---------------+------------+------------------+---------------+
+------------------------------------------------------------------------------------------------+
| Source:artifact:/usr/local/lib/python3.11/site-packages/setuptools-79.0.1.dist-info/METADATA   |
+------------+-------------------+---------------+------------+------------------+---------------+
| PACKAGE    | INSTALLED VERSION | FIX AVAILABLE | VULN COUNT | INTRODUCED LAYER | IN BASE IMAGE |
+------------+-------------------+---------------+------------+------------------+---------------+
| setuptools | 79.0.1            | Fix Available |          1 | # 7 Layer        | python        |
+------------+-------------------+---------------+------------+------------------+---------------+
+----------------------------------------------------------------------------------------------------+
| Source:artifact:/usr/local/lib/python3.11/site-packages/setuptools/_vendor/jaraco.context-5.3.0.di |
| st-info/METADATA                                                                                   |
+----------------+-------------------+---------------+------------+------------------+---------------+
| PACKAGE        | INSTALLED VERSION | FIX AVAILABLE | VULN COUNT | INTRODUCED LAYER | IN BASE IMAGE |
+----------------+-------------------+---------------+------------+------------------+---------------+
| jaraco-context | 5.3.0             | Fix Available |          1 | # 7 Layer        | python        |
+----------------+-------------------+---------------+------------+------------------+---------------+
+---------------------------------------------------------------------------------------------+
| Source:artifact:/usr/local/lib/python3.11/site-packages/setuptools/_vendor/wheel-0.45.1.dis |
| t-info/METADATA                                                                             |
+---------+-------------------+---------------+------------+------------------+---------------+
| PACKAGE | INSTALLED VERSION | FIX AVAILABLE | VULN COUNT | INTRODUCED LAYER | IN BASE IMAGE |
+---------+-------------------+---------------+------------+------------------+---------------+
| wheel   | 0.45.1            | Fix Available |          1 | # 7 Layer        | python        |
+---------+-------------------+---------------+------------+------------------+---------------+
+-----------------------------------------------------------------------------------------------+
| Source:artifact:/usr/local/lib/python3.11/site-packages/starlette-0.50.0.dist-info/METADATA   |
+-----------+-------------------+---------------+------------+------------------+---------------+
| PACKAGE   | INSTALLED VERSION | FIX AVAILABLE | VULN COUNT | INTRODUCED LAYER | IN BASE IMAGE |
+-----------+-------------------+---------------+------------+------------------+---------------+
| starlette | 0.50.0            | Fix Available |          5 | # 14 Layer       | --            |
+-----------+-------------------+---------------+------------+------------------+---------------+
Debian:13
+-------------------------------------------------------------------------------------------------------------------------------------------------+
| Source:os:/var/lib/dpkg/status                                                                                                                  |
+----------------+-----------------------------------+------------------+------------+-------------------------+------------------+---------------+
| SOURCE PACKAGE | INSTALLED VERSION                 | FIX AVAILABLE    | VULN COUNT | BINARY PACKAGES (COUNT) | INTRODUCED LAYER | IN BASE IMAGE |
+----------------+-----------------------------------+------------------+------------+-------------------------+------------------+---------------+
| acl            | 2.3.2-2+b1                        | No fix available |          2 | libacl1                 | # 0 Layer        | debian        |
| attr           | 1:2.5.2-3                         | No fix available |          1 | libattr1                | # 0 Layer        | debian        |
| bzip2          | 1.0.8-6                           | No fix available |          1 | libbz2-1.0              | # 0 Layer        | debian        |
| glibc          | 2.41-12+deb13u3                   | No fix available |         11 | libc-bin, libc6         | # 0 Layer        | debian        |
| gzip           | 1.13-1                            | No fix available |          2 | gzip                    | # 0 Layer        | debian        |
| ncurses        | 6.5+20250216-2                    | No fix available |          2 | libncursesw6... (4)     | # 7 Layer        | python        |
| pam            | 1.7.0-5                           | No fix available |          2 | libpam-modules... (4)   | # 0 Layer        | debian        |
| perl           | 5.40.1-6                          | No fix available |         16 | perl-base               | # 0 Layer        | debian        |
| shadow         | 1:4.17.4-2                        | No fix available |          1 | login.defs, passwd      | # 0 Layer        | debian        |
| sqlite3        | 3.46.1-7+deb13u1                  | No fix available |          5 | libsqlite3-0            | # 0 Layer        | debian        |
| systemd        | 257.13-1~deb13u1                  | No fix available |          3 | libsystemd0... (2)      | # 0 Layer        | debian        |
| tar            | 1.35+dfsg-3.1                     | No fix available |          3 | tar                     | # 0 Layer        | debian        |
| util-linux     | 1:2.41.5-0+deb13u1                | No fix available |          1 | bsdutils                | # 0 Layer        | debian        |
| util-linux     | 1:4.16.0-2+really2.41.5-0+deb13u1 | No fix available |          1 | login                   | # 0 Layer        | debian        |
| util-linux     | 2.41.5-0+deb13u1                  | No fix available |          1 | libblkid1... (7)        | # 0 Layer        | debian        |
| zlib           | 1:1.3.dfsg+really1.3.1-1+b1       | No fix available |          1 | zlib1g                  | # 0 Layer        | debian        |
+----------------+-----------------------------------+------------------+------------+-------------------------+------------------+---------------+

Hiding 25 number of vulnerabilities deemed unimportant, use --all-vulns to show them.
For the most comprehensive scan results, we recommend using the HTML output: `osv-scanner scan image --serve <image_name>`.
You can also view the full vulnerability list in your terminal with: `osv-scanner scan image --format vertical <image_name>`.
