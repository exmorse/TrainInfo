#!/usr/bin/python

import sys
import requests
import datetime
import json

STATION_URL = "http://www.viaggiatreno.it/viaggiatrenonew/resteasy/viaggiatreno/autocompletaStazione" 
SOLUTIONS_URL = "http://www.viaggiatreno.it/viaggiatrenonew/resteasy/viaggiatreno/soluzioniViaggioNew"
ORIGIN_URL = "http://www.viaggiatreno.it/viaggiatrenonew/resteasy/viaggiatreno/cercaNumeroTrenoTrenoAutocomplete"
RUNNING_INFO_URL = "http://www.viaggiatreno.it/viaggiatrenonew/resteasy/viaggiatreno/andamentoTreno"


def getStationCodeFromName(stationName):
        stationName = stationName.upper()

        req = requests.get(STATION_URL + "/" + stationName[0])
        if req.status_code != 200:
                print "Error requesting stations, " + str(req.status_code)
                return -1


        # Format: STATIONNAME|STATIONNUMBER\n
        stationsString = req.content
        stationList = stationsString.split('\n')

        stationElementList = []

        for line in stationList:
                stationElement = {}
                stationParts = line.split('|')
    
                if len(stationParts) == 2:
                        stationElement["name"] = stationParts[0]
                        stationElement["code"] = stationParts[1]
                        stationElementList.append(stationElement)

        for el in stationElementList:
                if el["name"] == stationName:
                        return el

        return None



# Returns the code (string) of origin station
def getOriginStationFromTrainNumber(trainNumber):
	req = requests.get(ORIGIN_URL + "/" + str(trainNumber))
	if req.status_code == 200:
		return req.content.split('-')[-1][:-1]
	return None



# Origin Station Code : where the train starts
# Source Station Code : where the user want to get on the train
### Origin Station is requested, because the train number may not be a unique identifier
def getRunningTrainInfo(trainNumber, originStationCode, srcStationCode):
	url = RUNNING_INFO_URL + "/" + originStationCode  + "/" + trainNumber
	req = requests.get(url)
	if req.status_code == 200:
		trainInfoJson = json.loads(req.content)

		info = {}
		info["delay"] = trainInfoJson["ritardo"]

		info["stops"] = trainInfoJson["fermate"]
		for stop in info["stops"]:	
			if stop["id"] == srcStationCode:
				info["expectedPlatform"] = stop["binarioProgrammatoArrivoDescrizione"]

				# Remove extra whitespace
				info["expectedPlatform"] = str(info["expectedPlatform"])[0:2]
	
				info["actualPlatform"] = stop["binarioEffettivoArrivoDescrizione"]
				info["nonStarted"] = trainInfoJson["nonPartito"]
				info["prov"] = trainInfoJson["provvedimento"]
				info["trainType"] = trainInfoJson["tipoTreno"]
				if info["trainType"] == "ST" and info["prov"] == 1:
					info["status"] = "Soppresso"	
				if info["trainType"] == "PG" and info["prov"] == 0:	
					info["status"] = "Regolare"
				else:
					info["status"] = "Unknown"

		# If stops is empty train is cancelled
		if len(info["stops"]) == 0:
			info["expectedPlatform"] = "-" 
			info["actualPlatform"] = "-" 
			info["nonStarted"] = True
			info["trainType"] = "-" 
			info["status"] = "Soppresso"  

		return info
	else:	
		return None


def getSolutionsFromStation(src, dst, solutionNumber=5):

	src["full_code"] = src["code"]
	dst["full_code"] = dst["code"]

	# Remove starting "S" and "0" in station codes
	for c in src["code"]:
		if c == 'S' or c == '0':
			src["code"] = src["code"][1:]
		else:
			break
	for c in dst["code"]:
		if c == 'S' or c == '0':
			dst["code"] = dst["code"][1:]
		else:
			break

	url = SOLUTIONS_URL + "/" + src["code"] + "/" + dst["code"]
	
	
	# Add current time in Format: YYYY-MM-DDTHH:MM:SS
	url = url + "/" + (datetime.datetime.now() - datetime.timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%S')

	req = requests.get(url)
	if req.status_code != 200:
		return None


	solutionsJson = json.loads(req.content)

	solutions = []
	
	for sol in solutionsJson["soluzioni"][0:solutionNumber]:
		s = {}
		v = sol["vehicles"][0]
		s["startTime"] = v["orarioPartenza"]
		s["tNum"] = v["numeroTreno"]
		s["cat"] = v["categoriaDescrizione"]
		s["trainTime"] = sol["durata"]
		s["nChanges"] = len(sol["vehicles"])-1
		s["orgStationNum"] = getOriginStationFromTrainNumber(s["tNum"])
		
		s_info = getRunningTrainInfo(s["tNum"], s["orgStationNum"], src["full_code"])
		s["info"] = s_info

		solutions.append(s)

	return solutions


if __name__ == "__main__":
	dstName = "Mirandola"
	srcName = "Bologna C.le"
	solNumber = 5
		
	print 

	print "Codici delle stazioni:"
	srcElement = getStationCodeFromName(srcName)
	if srcElement == None:
		print "Statione '" + srcName + "' non trovata"
		sys.exit(1)
	else:
		print "\t" + srcElement["name"] + "\t\t" + srcElement["code"]

	dstElement = getStationCodeFromName(dstName)
	if dstElement == None:
		print "Statione '" + dstName + "' non trovata"
		sys.exit(1)
	else:
		print "\t" + dstElement["name"] + "\t\t" + dstElement["code"]



	solutions = getSolutionsFromStation(srcElement, dstElement, solNumber)

	print
	print "ORARIO" + "\t\t\t" + "NUMERO" + "\t" + "DURATA" + "\t" + "RITARDO" + "\t" + "BINARIO" + "\t" + "STATO"	

	for s in solutions:
		if s["info"]["actualPlatform"] == None:
			s["info"]["actualPlatform"] = "?"

		print s["startTime"] + "\t" + s["tNum"] + "\t" + s["trainTime"] + "\t" + str(s["info"]["delay"]) + " min" + "\t" + str(s["info"]["expectedPlatform"]) + "("+str(s["info"]["actualPlatform"])+")" + "\t" + s["info"]["status"]
	print	
