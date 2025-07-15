#!/usr/bin/python
import os
import sys
import re
import hashlib
import argparse
import operator
from subprocess import Popen
from subprocess import PIPE
  
  
def parse_show(commit, search_file):
  p = Popen("git show %s:%s" % (commit, search_file), shell=True, stdout=PIPE, stderr=PIPE)
  (out, err) = p.communicate()
  if err != "":
    return ""
  return out
  
def parse_log(search_file, string, omit_directory, top):
  p = Popen("git log --stat --stat-width=10000 --pretty=oneline --format='\x11%H\x12'", shell=True, stdout=PIPE)
  (log, _) = p.communicate()
  
  files = {}
  commits = []
  version = {}
  changed = 0
  commit = ""
  current_version = ""
  
  for i in log.split('\n'):
    if re.match('\x11.*\x12', i):
      if changed == 0:
        version[commit] = current_version
      changed = 0
      commit = re.sub('[\x11\x12]', '', i)
      commits.append(commit)
  
    elif '|' in i:
      file = i.split()[0]
      if file == search_file:
        try:
          current_version = '-'.join(re.search(string, parse_show(commit, search_file)).groups()) + "-commitid-" + commit
          version[commit] = current_version
          changed = 1
        except:
          pass
  
      else:
        if files.has_key(file):
          files[file][commit] = []
        else:
          files[file] = {}
          files[file][commit] = []
  
  tmp = {}
  for file in files:
    if not re.match("^.*\.(php|asp|xml|sql|ini)$", file) and re.search(omit_directory, file) == None:
      tmp[file] = files[file]
  files = tmp
  
  if top != 0:
    files = dict(list(reversed(sorted(files.iteritems(), key=operator.itemgetter(1))))[:top])
  
  for file in files:
    for commit in files[file]:
      p = Popen("git show %s:%s" % (commit, file), shell=True, stdout=PIPE, stderr=PIPE)
      (out, err) = p.communicate()
      if err != "":
        continue
  
      files[file][commit] = hashlib.md5(out).hexdigest()
  
  return files, commits, version
  
def clone(url):
  path = url.split('/')[-1].split(".")[0]
  p = Popen("git clone %s" % url, shell=True, stdout=PIPE, stderr=PIPE)
  (out, err) = p.communicate()
  os.chdir(path)
  return path
  
if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-c", "--clone", help="Clone the repo first.", action="store_true")
  parser.add_argument("-u", "-p", "--url", "--path", help="Path or URL to the repository.", required=True)
  parser.add_argument("-f", "--file", help="File to search", required=True)
  parser.add_argument("-m", "--match", help="Regex to match line with version number (ie: '^\\\\\\$wp_version = \\x27([^']+)\\x27;$')", required=True)
  parser.add_argument("--omit-directory", help="Comma separated list of directories to omit.", default="")
  parser.add_argument("-t", "--top", help="Top 'n' files to use. (0 for unlimited)", default=10, type=int)
  args=parser.parse_args()
  
  if args.clone:
    print "Cloning: %s" % args.url
    path = clone(args.url)
  else:
    os.chdir(args.url)
    path = args.url
  
  (files, commits, version) = parse_log(args.file, args.match, "(" + '|'.join(args.omit_directory.split(",")) + ")", args.top)
  
  os.chdir("..")
  
  try:
    os.stat("sigs")
  except:
    os.mkdir("sigs")
  
  for file in files:
    f = open("sigs/%s-%s" % (path, file.rstrip("/").split("/")[-1]), "w")
    f.write("---\n")
    f.write("config:\n")
    f.write("  app_name: " + path + "\n")
    f.write("  check_file: " + file + "\n")
    f.write("sigs:\n")
    for revision in files[file]:
      try:
        f.write("  " + version[revision] + ": " + files[file][revision] + "\n")
      except:
        pass
	   f.close()
