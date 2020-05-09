# -*-coding:utf-8 -*-

#必须使用m3u8
#目前功能：根据所给的m3u8地址下载视频 自动判断是否需要解密
#		可从一个txt文件中读取m3u8并依次批量下载
#未来：引入多进程/多线程的同时不会串流 并且能正常显示进度（有点难度）

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import re
from urllib.parse import urljoin

import subprocess
from accesscmd import python2cmd

import winreg
import os

from Crypto.Cipher import AES
import binascii
import base64

import pdb

k=0

htmls=[]
results=[]

#---------------------------------设置代理------------------------------------------
#通过注册表获取代理设置
def getproxyip():
	key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
	try:
		proxy=winreg.QueryValueEx(key,"AutoConfigURL")
		ip=proxy[0]
		
		rule=re.compile(r"//.*?/")
		proxyip=rule.search(ip)
		proxyip=proxyip[0][2:-1]
		
		return proxyip
	
	except BaseException as e:
		proxyip="127.0.0.1:2080"
		print("使用默认代理")
		return proxyip


proxyip=getproxyip()
'''
if proxyip!=-1:
	proxy_dict={
		"http":"http://"+proxyip,
		"https":"https://"+proxyip
	}
else:
	proxy_dict={}
'''
proxy_dict={
	"http":"http://"+proxyip,
	"https":"https://"+proxyip
}
print(proxy_dict)


yeslist=['Y','y','']
nolist=['N','n']

choice=input("是否批量下载？（Y/n）（默认批量下载）")
#print(choice)
if choice in yeslist:
	htmltxtpath=input("请输入保存了m3u8.txt的本地目录:")
	htmltxtpath=htmltxtpath+"\\m3u8.txt"
	if not os.path.exists(htmltxtpath):
		print("未找到m3u8.txt文件 请检查后重试")
		exit(0)
	else:
		fhtml=open(htmltxtpath,"r")
		for line in fhtml:
			htmls.append(line)
		fhtml.close()
elif choice in nolist:
	onehtml=input("请输入m3u8文件的地址:")
	htmls.append(onehtml)

name2save=input("请输入想要保存的文件名:")


for k in range(len(htmls)):
	html=htmls[k]
	print("正在下载第",k+1,"个文件:",html)
	#f=open(r"C:\Users\ASUS\Desktop\m3u8_0"+str(k),"r")
	#m3u8=f.read()
	
	rm3u8=requests.get(html)
	m3u8=rm3u8.content.decode("utf-8")
	#pdb.set_trace()
	
	fm3u8=open(r"F:\\SomePythonProjects\\videos\\m3u8_temp.txt","w+")
	fm3u8.write(m3u8)
	fm3u8.close()
	fm3u8r=open(r"F:\\SomePythonProjects\\videos\\m3u8_temp.txt","r")

	for lline in fm3u8r:
		#result=re.search(r"(?:[A-Z]|[a-z]|\d|\/).*",lline)
		if lline[0]!="#":
			results.append(lline[:-1])


	orilinks=results
	links=[]
	for link in orilinks:
		if ".ts" in link:
			links.append(link)
	#print(links[0])

	keyhtml=re.search(r"\".*?\"",m3u8)
	if keyhtml:
		keyhtml=keyhtml.group(0)
		keyhtml=keyhtml[1:-1]
		#print(keyhtml[:-1])

	ivresult=re.search(r"(?:0x).*",m3u8)
	if ivresult:
		ivresult=ivresult.group(0)[2:]
	#print(ivresult)


	#----------------------------------------------构造请求头 获取密钥-----------------------------------
	
	if keyhtml:
		keyhtml=urljoin(html,keyhtml)
		#print(keyhtml)
		#rkey=requests.get(keyhtml,headers=header)
		rkey=requests.get(keyhtml)
		'''
		fkey=open(r"F:\SomePythonProjects\videos\key_temp.txt","w+")
		fkey.write(rkey.text)
		fkey.close()
		'''
		#等会儿解密使用
		# .text会返回unicode编码类型的网页内容 而.content才会返回byte类型的原始内容
		#key=rkey.text.encode("utf-8")
		key=rkey.content

		mode=AES.MODE_CBC
		if ivresult:
			#print(ivresult)
			iv=binascii.a2b_hex(ivresult)
			#print(iv)
			cryptos=AES.new(key,mode,iv)
		else:
			cryptos=AES.new(key,mode)

	#-------------------------------------------------------------------------------------------------------------------
	
	i=0

	#路径皆使用双杠 照顾好用但愚蠢的ffmpeg
	#若不存在 则创建一个单独的文件夹
	videopath=r"F:\\SomePythonProjects\\videos\\"+name2save
	videopath+="_0"+str(k)
	if not os.path.exists(videopath):
		os.mkdir(videopath)
	#用于记录ts文件名 方便使用ffmpeg合并
	videopath+=r"\\"

	findex=open(videopath+name2save+".txt","w+")

	#设置个进度条长度 单纯为了单行显示的美观
	tq=tqdm(links,ncols=60)
	for link in tq:
		if i<=9:
			videoname=name2save+"0"+str(i)+".ts"
		else:
			videoname=name2save+str(i)+".ts"
		i+=1
		f=open(videopath+videoname,"wb+")
		#先规范化一下路径 可能为相对路径

		link=urljoin(html,link)
		#header2['path']+=link
		#print(header2)
		#print(link)
		header3={
			"referer": html,
			"user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3741.400 QQBrowser/10.5.3863.400"
		}
		ts=requests.get(link,headers=header3)
		
		#有的网站有重定向 用head方法访问试试获取重定向页面

		if ts.status_code!=200:
			print("网站返回值：",ts.status_code)
			ts=requests.head(link,headers=header3)
			try:
				if ts.headers['location']:
					redirect2=ts.headers['location']
					#print(redirect2)
					ts=requests.head(redirect2)
			except:
				print("尝试一些新的方法吧")
				exit(0)
		#print(ts.content)
		
		if keyhtml:
			#解密ts内容再写入
			ts_dec=cryptos.decrypt(ts.content)
		
			f.write(ts_dec)
		else:
			f.write(ts.content)
		findex.write(r"file "+videopath+videoname)
		findex.write("\n")
		f.close()

	tq.close()
	findex.close()
	ts.close()

	indexfilename=videopath+name2save+".txt"
	print(indexfilename)
	videofilename=videopath+name2save+".mp4"
	print(videofilename)
	ffcommand=["ffmpeg","-f","concat","-safe","0","-i",indexfilename,"-c","copy",videofilename]

	python2cmd(ffcommand)
	
#ffmpeg -f concat -safe 0 -i F:\SomePythonProjects\videos\00.txt -c copy F:\SomePythonProjects\videos\test00.mp4
