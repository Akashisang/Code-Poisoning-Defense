# []--------------------------------------------------------[]
#  |                      LGI.py                            |
# []--------------------------------------------------------[]
#  |                                                        |
#  | AUTHOR:     M.F.Somers                                 |
#  | VERSION:    1.00, June 2010.                           |
#  | USE:        Interface class code...                    |
#  |                                                        |
# []--------------------------------------------------------[]
#
# Copyright (C) 2010 M.F. Somers, Theoretical Chemistry Group, Leiden University
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

import sys, os, httplib, urlparse, binascii, xml.dom.minidom;

if( sys.version_info >= ( 2, 6 ) ):             # if we have python 2.6 or more, we have ssl...
	import socket, ssl;

# ---------------------------------------------------------------------------------------------------------

class LGI_Client:

	# init the class with parameters or defaults read in from ~/.LGI 
	def __init__( self, URL = None, Project = None, User = None, Groups = None, Certificate = None, PrivateKey = None, CA_Chain = None ):
                self._URL = None;
                self._Project = None;
                self._User = None;
                self._Groups = None;
                self._Certificate = None;
                self._PrivateKey = None;
                self._CA_Chain = None;

		if( URL ): self._URL = URL;
		if( Project ): self._Project = Project;
		if( User ): self._User = User;
		if( Groups ): self._Groups = Groups
		if( Certificate ): self._Certificate = Certificate;
		if( CA_Chain ): self._CA_Chain = CA_Chain;
		if( PrivateKey ): self._PrivateKey = PrivateKey;
		
		self._Connection = None;

		if( not self._URL ): self._URL = self.__GetDefaultConfigFromFile( "defaultserver" );
		if( not self._Project ): self._Project = self.__GetDefaultConfigFromFile( "defaultproject" );
		if( not self._User ): self._User = self.__GetDefaultConfigFromFile( "user" );
		if( not self._Groups ): self._Groups = self.__GetDefaultConfigFromFile( "groups" );
                if( not self._Certificate ): self._Certificate = os.getenv( "HOME" ) + "/.LGI/certificate";
                if( not self._PrivateKey ): self._PrivateKey = os.getenv( "HOME" ) + "/.LGI/privatekey";
                if( not self._CA_Chain ): self._CA_Chain = os.getenv( "HOME" ) + "/.LGI/ca_chain";

                dURL = urlparse.urlparse( self._URL );

                if( dURL[ 0 ] != 'https' ): 
			sys.exit( "LGI_Client class not correctly setup" );
		else:
			self._Host = dURL[ 1 ];
			self._Path = dURL[ 2 ];

	# actually setup the ssl connection to the server
	def Connect( self ):
		if( not self._Connection ): 
			self._Connection = self.__HTTPSConnection( self._Host, PrivateKey = self._PrivateKey, Certificate = self._Certificate, CA_Chain = self._CA_Chain );

	# request the jobs state
	def GetJobState( self, JobId ):
		Vars = {};
		Vars[ 'project' ] = self._Project;
		Vars[ 'user' ] = self._User;
		Vars[ 'groups' ] = self._Groups;
		if( JobId ): Vars[ 'job_id' ] = JobId;
		return( self.__PostToServer( "/interfaces/interface_job_state.php", Vars ) );

	# get a list of jobs for given application and state
	def GetJobList( self, Application = None, State = None, Start = None, Limit = None ):
		Vars = {};
		Vars[ 'project' ] = self._Project;
		Vars[ 'user' ] = self._User;
		Vars[ 'groups' ] = self._Groups;
		if( Application ): Vars[ 'application' ] = Application;
		if( State ): Vars[ 'state' ] = State;
		if( Start ): Vars[ 'start' ] = Start;
		if( type( Limit ) == type( 1 ) ): Vars[ 'limit' ] = Limit;
		return( self.__PostToServer( "/interfaces/interface_job_state.php", Vars ) );

	# delete a job
	def DeleteJob( self, JobId ):
		Vars = {};
		Vars[ 'project' ] = self._Project;
		Vars[ 'user' ] = self._User;
		Vars[ 'groups' ] = self._Groups;
		if( JobId ): Vars[ 'job_id' ] = JobId;
		return( self.__PostToServer( "/interfaces/interface_delete_job.php", Vars ) );

	# get the resource list	
	def GetResourceList( self ):
		Vars = {};
		Vars[ 'project' ] = self._Project;
		Vars[ 'user' ] = self._User;
		Vars[ 'groups' ] = self._Groups;
		return( self.__PostToServer( "/interfaces/interface_project_resource_list.php", Vars ) );

	# get the project server list
	def GetServerList( self ):
		Vars = {};
		Vars[ 'project' ] = self._Project;
		Vars[ 'user' ] = self._User;
		Vars[ 'groups' ] = self._Groups;
		return( self.__PostToServer( "/interfaces/interface_project_server_list.php", Vars ) );

	# submit a job for given application and options
	def SubmitJob( self, Application, TargetResources = "any", Input = None, JobSpecifics = None, WriteAccess = None, ReadAccess = None, FileList = [] ):
		Vars = {};
		Vars[ 'project' ] = self._Project;
		Vars[ 'user' ] = self._User;
		Vars[ 'groups' ] = self._Groups;
		Vars[ 'number_of_uploaded_files' ] = 0;
		Files = {};
		if( Application ): Vars[ 'application' ] = Application;
		if( TargetResources ): Vars[ 'target_resources' ] = TargetResources;
		if( WriteAccess ): Vars[ 'write_access' ] = WriteAccess;
		if( ReadAccess ): Vars[ 'read_access' ] = ReadAccess;
		if( JobSpecifics ): Vars[ 'job_specifics' ] = JobSpecifics;
		if( Input ): Vars[ 'input' ] = binascii.b2a_hex( Input );
		if( FileList ):
			for FileName in FileList:
				Vars[ 'number_of_uploaded_files' ] = Vars[ 'number_of_uploaded_files' ] + 1;	
				File = open( FileName, "r" );
				Files[ 'uploaded_file_%d' % Vars[ 'number_of_uploaded_files' ] ] = ( FileName, File.read() );
				File.close();
		return( self.__PostToServer( "/interfaces/interface_submit_job.php", Vars, Files ) );

	# if the class was setup with a repository URL, use this method to get a listing
	def ListRepository( self ):
		Vars = {};
		Vars[ 'repository' ] = self._Path[ self._Path.rfind( "/" ) + 1 : len( self._Path ) ];
		return( self.__PostToServer( API = None, Path = self._Path[ 0 : self._Path.rfind( "/" ) + 1 ] + "../repository_content.php", Variables = Vars ) );

	# if the class was setup with a repository URL, use this method to download some files
	def DownLoadFiles( self, Files, Where = None ):
		if( not self._Connection ): self.Connect();
		for FileName in Files:
			BaseFileName = FileName[ FileName.rfind( '/' ) + 1 : len( FileName ) ];
			if( Where ):
				File = open( Where + "/" + BaseFileName, "w" );
			else:
				File = open( FileName, "w" );
			try:
				self._Connection.request( "GET", self._URL + "/" + BaseFileName );
				Response = self._Connection.getresponse();
			except:
				self._Connection.close();
				self._Connection.connect();	
				self._Connection.request( "GET", self._URL + "/" + BaseFileName );
				Response = self._Connection.getresponse();
			Data = Response.read( 4096 );
			while( Data ):
				File.write( Data );
				Data = Response.read( 4096 );
			File.close();
			Response.close();

	# if the class was setup with a repository URL, use this method to upload some files
	def UpLoadFiles( self, Files ):
		if( not self._Connection ): self.Connect();
		for FileName in Files:
			BaseFileName = FileName[ FileName.rfind( '/' ) + 1 : len( FileName ) ];
			File = open( FileName, "r" );
			Headers = { "Content-Length": str( os.fstat( File.fileno() ).st_size ) };
			try:
				self._Connection.request( "PUT", self._URL + "/" + BaseFileName, None, Headers );
				Data = File.read( 4096 );
				while( Data ):
					self._Connection.send( Data );
					Data = File.read( 4096 );
				Response = self._Connection.getresponse();
			except:
				self._Connection.close();
				self._Connection.connect();
				File.seek( 0 );

				self._Connection.request( "PUT", self._URL + "/" + BaseFileName, None, Headers );
				Data = File.read( 4096 );
				while( Data ):
					self._Connection.send( Data );
					Data = File.read( 4096 );
				Response = self._Connection.getresponse();

			Response.read();
			Response.close();
			File.close();
	
	# if the class was setup with a repository URL, use this method to delete some files
	def DeleteFiles( self, Files ):
		if( not self._Connection ): self.Connect();
		for FileName in Files:
			BaseFileName = FileName[ FileName.rfind( '/' ) + 1 : len( FileName ) ];
			try:
				self._Connection.request( "DELETE", self._URL + "/" + BaseFileName );
				Response = self._Connection.getresponse();
			except:
				self._Connection.close();
				self._Connection.connect();
				self._Connection.request( "DELETE", self._URL + "/" + BaseFileName );
				Response = self._Connection.getresponse();
			Response.read();
			Response.close();

	# close the connection
	def Close( self ):
		if( self._Connection ):
			self._Connection.close();
			self._Connection = None;

	def __del__( self ):
		self.Close();
	
	def __GetDefaultConfigFromFile( self, Name ):
		File = open( os.getenv( "HOME" ) + "/.LGI/" + Name, "r" );	
		Data = File.read();
		File.close();
		return( Data.rstrip( "\n\r\t " ) );
	
	def __PostToServer( self, API, Variables = {}, Files = {}, Path = None ):
		if( not self._Connection ): self.Connect();

                Boundary = "@$_Th1s_1s_th3_b0und@ry_@$";
                List = [];

                if( Variables ):
			for Key in Variables:
				List.append( "--" + Boundary );
				List.append( 'Content-Disposition: form-data; name="%s"' % Key );
				List.append( "" );
				List.append( str( Variables[ Key ] ) );

		if( Files ):
			for Key in Files:
				List.append( "--" + Boundary );
				List.append( 'Content-Disposition: form-data; name="%s"; filename="%s"' % ( Key, Files[ Key ][ 0 ] ) );
        			List.append( "Content-Type: application/octet-stream" )
				List.append( "" );
				List.append( Files[ Key ][ 1 ] );
		List.append( "--" + Boundary + "--" );
		List.append( "" );				

		Body = "\r\n".join( List );
		Headers = { "Content-type": "multipart/form-data; boundary=%s" % Boundary, "Accept": "text/plain" };

		try:
			if( Path ):
				self._Connection.request( "POST", Path, Body, Headers );
			else:
				self._Connection.request( "POST", self._Path + API, Body, Headers );

			Response = self._Connection.getresponse();

		except:
			self._Connection.close();
			self._Connection.connect();
			
			if( Path ):
				self._Connection.request( "POST", Path, Body, Headers );
			else:
				self._Connection.request( "POST", self._Path + API, Body, Headers );

			Response = self._Connection.getresponse();

		Data = Response.read();
		Response.close();
		return( self.__NodesToDict( xml.dom.minidom.parseString( Data ) ) );

	class __NotATextNode:
		pass;

	def __NodesToDict( self, Node ):
                Counts = {};
		Dict = {};
	
		for n in Node.childNodes:
			if( n.nodeType != n.ELEMENT_NODE ):
				continue;

			NodeName = n.nodeName.encode();

			if( Counts.has_key( n.nodeName ) ):
				Counts[ NodeName ] = Counts[ NodeName ] + 1;	
				Dict[ NodeName ] = [];
			else:
				Counts[ NodeName ] = 1;
		
		for n in Node.childNodes:
			if( n.nodeType != n.ELEMENT_NODE ):
				continue;

			NodeName = n.nodeName.encode();

			Attributes = {};

			if( n.attributes ):
				for nn in range( n.attributes.length ):
					AttrName =  n.attributes.item( nn ).nodeName.strip( "\n\r\t " ).encode();
					AttrValue = n.attributes.item( nn ).nodeValue.strip( "\n\r\t " );
					if( AttrValue.isdigit() ):
						AttrValue = int( AttrValue );
					else:
						AttrValue = AttrValue.encode();
					Attributes[ AttrName ] = AttrValue;
        
			try:
				Text = "";

				for nn in n.childNodes:
					if( nn.nodeType == nn.TEXT_NODE ):
						Text = Text + nn.nodeValue;
					else:
						raise self.__NotATextNode;

				Text = Text.strip( "\n\r\t " );

			except self.__NotATextNode:

				if( Attributes ):
					SubDict = { 'attributes': Attributes, NodeName: self.__NodesToDict( n ) };
				else:
					SubDict = self.__NodesToDict( n );
	
				if( Counts[ NodeName ] > 1 ):
					Dict[ NodeName ].append( SubDict );
				else: 
					Dict[ NodeName ] = SubDict;

				continue;

			if( NodeName == "input" or NodeName == "output" ):
				Text = binascii.a2b_hex( Text );
			else:
				if( Text.isdigit() ):
					Text = int( Text );
				else:
					Text = Text.encode();

			if( Attributes ):
				SubText = { 'attributes': Attributes, NodeName: Text };
			else:
				SubText = Text;

			if( Counts[ NodeName ] > 1 ):
				Dict[ NodeName ].append( SubText );
			else:
				Dict[ NodeName ] = SubText;
	
		return Dict;

	if( sys.version_info >= ( 2, 6 ) ):             # if we have python 2.6 or more, we have ssl...

		class __HTTPSConnection( httplib.HTTPConnection ):
    			def __init__( self, Host, Port = 443, PrivateKey = None, Certificate = None, CA_Chain = None, SSL_Version = ssl.PROTOCOL_SSLv23, Certificate_Required = ssl.CERT_REQUIRED, Strict = None ):
        			httplib.HTTPConnection.__init__( self, Host, Port, Strict );
        			self._PrivateKey = PrivateKey;
        			self._Certificate = Certificate;
        			self._CA_Chain = CA_Chain;
        			self._SSL_Version = SSL_Version;
        			self._Certificate_Required = Certificate_Required;

    			def connect( self ):
        			ASocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM );
        			self.sock = ssl.wrap_socket( ASocket, keyfile=self._PrivateKey, certfile=self._Certificate, 
				            ca_certs=self._CA_Chain, ssl_version=self._SSL_Version, cert_reqs=self._Certificate_Required );
        			self.sock.connect( ( self.host, self.port ) );

	else:

		class __HTTPSConnection( httplib.HTTPSConnection ):
    			def __init__( self, Host, Port = 443, PrivateKey = None, Certificate = None, CA_Chain = None, SSL_Version = None, Certificate_Required = None, Strict = None ):
        			httplib.HTTPSConnection.__init__( self, Host, Port, PrivateKey, Certificate, Strict );

# ---------------------------------------------------------------------------------------------------------

