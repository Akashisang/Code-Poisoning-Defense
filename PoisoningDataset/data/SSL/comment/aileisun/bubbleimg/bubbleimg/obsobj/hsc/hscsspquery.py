""" 
do sql search on hsc data base

this is modified from hscSspQuery.py version 20160120.1 by ALS on 2017/05/11

  --------------------------------------------------------------------------------
  Original Instructions:
  https://hscdata.mtk.nao.ac.jp/hsc_ssp/dr1/common/cas_script.html
  https://hsc-gitlab.mtk.nao.ac.jp/snippets/13
  --------------------------------------------------------------------------------
  usage:

  $ echo "SELECT now();" > test.sql
  $ python hscSspQuery.py test.sql -u "your_STARS_account" > result.csv
  password? (input your STARS password)

  OR

  bash)
  ### input your STARS username and password
  $ export HSC_SSP_CAS_USERNAME
  $ read -s HSC_SSP_CAS_USERNAME
  $ export HSC_SSP_CAS_PASSWORD
  $ read -s HSC_SSP_CAS_PASSWORD

  $ python hscSspQuery.py test1.sql -u "your_STARS_account" > result1.csv
  $ python hscSspQuery.py test2.sql -u "your_STARS_account" > result2.csv
  $ python hscSspQuery.py test3.sql -u "your_STARS_account" > result3.csv
  --------------------------------------------------------------------------------

"""
