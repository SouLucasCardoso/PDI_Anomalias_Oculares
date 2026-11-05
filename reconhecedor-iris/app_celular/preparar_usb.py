"""Baixa apenas Platform-Tools estável oficial e verifica checksum do catálogo."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'.runtime/android_sdk'


def main():
    base='https://dl.google.com/android/repository/'
    xml=urllib.request.urlopen(base+'repository2-3.xml',timeout=30).read()
    tree=ET.fromstring(xml)
    candidates=[]
    for package in tree.findall('remotePackage'):
        if package.attrib.get('path')!='platform-tools':continue
        channel=package.find('channelRef')
        if channel is not None and channel.attrib['ref']!='channel-0':continue
        revision=package.find('revision')
        version=tuple(int(revision.findtext(x,'0')) for x in ('major','minor','micro'))
        for archive in package.findall('archives/archive'):
            if archive.findtext('host-os')=='windows':candidates.append((version,archive.find('complete')))
    version,complete=max(candidates,key=lambda x:x[0])
    url=base+complete.findtext('url')
    data=urllib.request.urlopen(url,timeout=60).read()
    if len(data)!=int(complete.findtext('size')) or hashlib.sha1(data).hexdigest()!=complete.findtext('checksum'):
        raise ValueError('Download não confere com o catálogo oficial')
    DEST.mkdir(parents=True,exist_ok=True)
    archive=DEST/'platform-tools.zip';archive.write_bytes(data)
    with zipfile.ZipFile(archive) as zipped:
        for entry in zipped.infolist():
            target=(DEST/entry.filename).resolve()
            if not target.is_relative_to(DEST.resolve()):raise ValueError('Caminho inválido no pacote')
        zipped.extractall(DEST)
    adb=DEST/'platform-tools/adb.exe'
    output=subprocess.check_output([str(adb),'version'],text=True)
    report=dict(version='.'.join(map(str,version)),channel='stable',url=url,
        archive_sha1=hashlib.sha1(data).hexdigest(),archive_sha256=hashlib.sha256(data).hexdigest(),
        adb_sha256=hashlib.sha256(adb.read_bytes()).hexdigest(),adb_version=output,
        repository_sha256=hashlib.sha256(xml).hexdigest(),device_or_usb_authorization_tested=False)
    (DEST/'PROVENIENCIA.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    out=ROOT/'outputs/app_celular_2026-11-05';out.mkdir(parents=True,exist_ok=True)
    (out/'ANDROID_TOOLS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(output)
    print('Preparado. Nenhuma configuração do celular foi alterada.')


if __name__=='__main__':main()
