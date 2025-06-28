#
#  Copyright 2014 Epsilon232 <2014ryan@student.ncc.vic.edu.au>
# 
# Dennis is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from Bot import Bot
from Entity import Entity
from World import World
#from Effect import Effect
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Cipher import AES
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from DataTypes import *
from Block import Block

class PacketDispatch():
	def __init__(self, network):
		self.network = network;
		self.bot = network.bot;

	# Keep alive
	def Packet0x00(self, buff):
		KeepAliveID = buff.readVarInt()
		if(KeepAliveID):
			response = Buffer();
			response.writeVarInt(0);
			response.writeVarInt(KeepAliveID);
			self.network.packetSend.append(response);

	def Packet0x01(self, buff):
		if self.bot.joined:
			if self.bot.enc:
				Time = buff.readBool()
			else:
				#print(buff.string.encode("hex"))
				ServerID = buff.readString()
				PublicKey = buff.readString()
				VerifyToken = buff.readString()
				self.bot.encryption = True
				self.bot.cipher = AES.new(self.bot.secret, AES.MODE_CFB, self.bot.secret)
				self.bot.decipher = AES.new(self.bot.secret, AES.MODE_CFB, self.bot.secret)
				key2 = RSA.importKey(PublicKey)
				key = PKCS1_v1_5.new(key2)
		else:
			EntityID = buff.readInt()
			Gamemode = buff.readUnsignedByte()
			Dimension = buff.readByte()
			Difficulty = buff.readUnsignedByte()
			MaxPlayers = buff.readUnsignedByte()
			LevelType = buff.readString()
			ReducedDebugInfo = buff.readBool()
			self.bot.joined = True

	# Alive: Chat update
	# Dead: login info
	def Packet0x02(self, buff):
		if self.bot.loggedIn == False:
			self.bot.UUID = buff.readString()
			self.bot.Username = buff.readString()
			self.bot.loggedIn = True
		else:
			JSONData = buff.readString()
			Position = buff.readByte()
	
	# Time update
	def Packet0x03(self, buff):
		if len(buff.string) == 16:
			self.bot.world.worldAge = buff.readLong()
			self.bot.world.timeOfDay = buff.readLong()
		else:
			self.network.compressionThreshold = buff.readVarInt()
	
	# Entity Equipment
	def Packet0x04(self, buff):
		EntityID = buff.readVarInt()
		Slot = buff.readShort()
		Item = buff.readBool() # BOOL
		
		entity = self.bot.world.getEntity(EntityID);
		entity.slot = Slot;
		entity.item = Item;
	
	# Spawn Position 
	def Packet0x05(self, buff):
		self.bot.location = buff.readPosition();
	
	# Update Health
	def Packet0x06(self, buff):
		self.bot.health = buff.readFloat();
		self.bot.food = buff.readVarInt();
		self.bot.foodSaturation = buff.readFloat();
	
	# Respawn
	def Packet0x07(self, buff):
		self.bot.world.dimension = buff.readInt()
		self.bot.world.difficulty = buff.readUnsignedByte()
		self.bot.gamemode = buff.readUnsignedByte()
		self.bot.world.levelType = buff.readString()
		
	# Player position and look
	def Packet0x08(self, buff):
		X = buff.readDouble()
		Y = buff.readDouble()
		Z = buff.readDouble()
		Yaw = buff.readFloat()
		Pitch = buff.readFloat()
		Flags = buff.readByte()
		
		#tempoary for login
		response = Buffer()
		response.writeVarInt(0x06)
		response.writeDouble(X)
		response.writeDouble(Y)
		response.writeDouble(Z)
		response.writeFloat(Yaw)
		response.writeFloat(Pitch)
		response.writeBool(True)
		self.network.packetSend.append(response)

		if Flags%2 != 0:
			X += self.bot.location.x;
			Flags -= 1;
		Flags >>= 1;
		if Flags%2 != 0:
			Y += self.bot.location.y;
			Flags -= 1;
		Flags >>= 1;
		if Flags%2 != 0:
			Z += self.bot.location.z;
			Flags -= 1;
		Flags >>= 1;
		if Flags%2 != 0:
			Yaw += self.bot.rotation.x;
			Flags -= 1;
		Flags >>= 1;
		if Flags%2 != 0:
			Pitch += self.bot.rotation.y;
			Flags -= 1;
			
		self.bot.rotation.set(Yaw, Pitch, 0);
		self.bot.location.set(X, Y, Z);
		
	
	# Held item changed
	def Packet0x09(self, buff):
		self.bot.slot = buff.readByte()
	
	# Use bed
	def Packet0x0A(self, buff):
		EntityID = buff.readVarInt();
		Location = buff.readPosition();
		entity = self.bot.world.getEntity(EntityID);
		entity.bedLocation = Location;
	
	# Animation
	def Packet0x0B(self, buff):
		EntityID = buff.readVarInt()
		Animation = buff.readUnsignedByte()
		entity = self.bot.world.getEntity(EntityID);
		entity.animation = Animation;
		
	# Spawn player
	def Packet0x0C(self, buff):
		EntityID = buff.readVarInt();
		PlayerUUID = (buff.readLong() << 8) + buff.readLong();
		X = buff.readInt();
		Y = buff.readInt();
		Z = buff.readInt();
		Yaw = buff.readByte();
		Pitch = buff.readByte();
		CurrentItem = buff.readShort();
		Metadata = buff.readMetadata();
		
		entity = self.bot.world.getEntity(EntityID);
		entity.UUID = PlayerUUID;
		entity.location.set(X, Y, Z);
		entity.rotation.set(Yaw, Pitch, 0);
		entity.currentItem = CurrentItem;
		entity.metadata = Metadata;
	
	# Collect item
	def Packet0x0D(self, buff):
		CollectedEntityID = buff.readVarInt()
		CollectorEntityID = buff.readVarInt()
	
	#
	def Packet0x0E(self, buff):
		EntityID = buff.readVarInt()
		Type = buff.readByte()
		X = buff.readInt()
		Y = buff.readInt()
		Z = buff.readInt()
		Pitch = buff.readByte()
		Yaw = buff.readByte()
		Data = buff.readObjectData() # Add this later
		
		entity = self.bot.world.getEntity(EntityID);
		entity.type = Type;
		entity.location.set(X, Y, Z);
		entity.rotation.set(Yaw, Pitch, 0);
		
	# Spawn mob
	def Packet0x0F(self, buff):
		EntityID = buff.readVarInt()
		Type = buff.readUnsignedByte()
		X = buff.readInt()
		Y = buff.readInt()
		Z = buff.readInt()
		Yaw = buff.readByte()
		Pitch = buff.readByte()
		HeadPitch = buff.readByte() # No idea what this is
		VelocityX = buff.readShort()
		VelocityY = buff.readShort()
		VelocityZ = buff.readShort()
		Metadata = buff.readMetadata()
		
		entity = self.bot.world.getEntity(EntityID);
		entity.type = Type;
		entity.location.set(X, Y, Z);
		entity.rotation.set(Yaw, Pitch, 0);
		entity.velocity.set(VelocityX, VelocityY, VelocityZ);
		entity.metadata = Metadata;
	
	# Spawn painting
	def Packet0x10(self, buff):
		EntityID = buff.readVarInt();
		Title = buff.readString();
		Location = buff.readPosition();
		Direction = buff.readUnsignedByte();
		
		entity = self.bot.world.getNonLiving(EntityID);
		entity.title = Title;
		entity.location = Location;
		entity.direction = Direction;
		
	# Spawn Experience Orb 
	def Packet0x11(self, buff):
		EntityID = buff.readVarInt()
		X = buff.readInt()
		Y = buff.readInt()
		Z = buff.readInt()
		Count = buff.readShort()
		
		entity = self.bot.world.getOrb(EntityID);
		entity.location.set(X, Y, Z);
		entity.XP = Count;
	
	# Entity Velocity 
	def Packet0x12(self, buff):
		EntityID = buff.readVarInt()
		VelocityX = buff.readShort()
		VelocityY = buff.readShort()
		VelocityZ = buff.readShort()
		
		entity = self.bot.world.getEntity(EntityID);
		entity.velocity.set(VelocityX, VelocityY, VelocityZ);
	
	# Destroy Entities 
	def Packet0x13(self, buff):
		Count = buff.readVarInt()
		EntityIDs = []
		while Count > 0:
			EntityIDs.append(buff.readVarInt())
			Count -= 1
		
		for entity in EntityIDs:
			self.bot.world.delEntity(entity);
		
	# Create entity
	def Packet0x14(self, buff):
		EntityID = buff.readVarInt()
		
		self.bot.world.getEntity(EntityID);
	
	# Entity Relative Move 
	def Packet0x15(self, buff):
		EntityID = buff.readVarInt()
		DX = buff.readByte()
		DY = buff.readByte()
		DZ = buff.readByte()
		OnGround = buff.readBool()
		
		entity = self.bot.world.getEntity(EntityID);
		entity.location.add(DX/32.0, DY/32.0, DZ/32.0);
		entity.onGround = OnGround;
	
	# Entity Look
	def Packet0x16(self, buff):
		EntityID = buff.readVarInt()
		Yaw = buff.readByte()
		Pitch = buff.readByte()
		OnGround = buff.readBool()
		
		entity = self.bot.world.getEntity(EntityID);
		# TODO: Fix rotation on other methods
		entity.rotation.add((Yaw/64)*90, (Pitch/64)*90, 0);
		entity.onGround = OnGround;

	# Entity Look and Relative Move 
	def Packet0x17(self, buff):
		EntityID = buff.readVarInt()
		DX = buff.readByte()
		DY = buff.readByte()
		DZ = buff.readByte()
		Yaw = buff.readByte()
		Pitch = buff.readByte()
		OnGround = buff.readBool()
		
		entity = self.bot.world.getEntity(EntityID);
		entity.rotation.add((Yaw/64)*90, (Pitch/64)*90, 0);
		entity.location.add(DX/32.0, DY/32.0, DZ/32.0);
		entity.onGround = OnGround;
	
	# Entity Teleport
	def Packet0x18(self, buff):
		EntityID = buff.readVarInt()
		X = buff.readInt()
		Y = buff.readInt()
		Z = buff.readInt()
		Yaw = buff.readByte()
		Pitch = buff.readByte()
		OnGround = buff.readBool()
		
		entity = self.bot.world.getEntity(EntityID);
		entity.rotation.add((Yaw/64)*90, (Pitch/64)*90, 0);
		entity.location.set(X, Y, Z);
		entity.onGround = OnGround;
	
	#  Entity Head Look
	def Packet0x19(self, buff):
		EntityID = buff.readVarInt()
		HeadYaw = buff.readByte()
		
		entity = self.bot.world.getEntity(EntityID);
		#entity.rotation.add();
		# No idea how to use HeadYaw in format 2p/256
	
	# Entity status
	def Packet0x1A(self, buff):
		EntityID = buff.readInt()
		EntityStatus = buff.readByte()
		
		entity = self.bot.world.getEntity(EntityID);
		entity.status = EntityStatus;
	
	# Attach Entity
	def Packet0x1B(self, buff):
		EntityID = buff.readInt()
		VehicleID = buff.readInt()
		Leash = buff.readBool()
		
		entity = self.bot.world.getPlayer(EntityID);
		entity.vehicle = VehicleID;
		entity.leash = Leash;
	
	# Entity Metadata 
	def Packet0x1C(self, buff):
		EntityID = buff.readVarInt()
		Metadata = buff.readMetadata()
		
		entity = self.bot.world.getPlayer(EntityID);
		entity.metadata = Metadata;
	
	# Entity Effect 
	def Packet0x1D(self, buff):
		EntityID = buff.readVarInt()
		EffectID = buff.readByte()
		Amplifier = buff.readByte()
		Duration = buff.readVarInt()
		HideParticles = buff.readBool()
		
		entity = self.bot.world.getPlayer(EntityID);
		effect = entity.getEffect(EffectID);
		effect.amplifier = Amplifier;
		effect.duration = Duration;
		effect.hideParticles = HideParticles;
		
	#  Remove Entity Effect 
	def Packet0x1E(self, buff):
		EntityID = buff.readVarInt()
		EffectID = buff.readByte()
		
		entity = self.bot.world.getEntity(EntityID);
		entity.delEffect(EffectID);
		
	# Set Experience 
	def Packet0x1F(self, buff):
		Experiencebar = buff.readFloat() # TODO: Find out if we need this
		Level = buff.readVarInt()
		TotalExperience = buff.readVarInt()
		
		self.bot.XP = TotalExperience;
		self.bot.level = Level;
	
	# Entity Properties
	def Packet0x20(self, buff):
		EntityID = buff.readVarInt()
		Count = buff.readInt()
		
		entity = self.bot.world.getEntity(EntityID);
		
		for i in range(Count):
			Key = buff.readString();
			Value = buff.readDouble();
			modifierArrayLength = buff.readVarInt();
			
			property = entity.getProperty(Key);
			property.value = Value;
			
			for j in range(modifierArrayLength):
				UUID = 0;
				for k in range (4):
					UUID += buff.readInt() << ((3-k)*32);
				Amount = buff.readDouble();
				Opperation = buff.readByte();
				
				modifier = property.getModifier(UUID);
				modifier.amount = Amount;
				modifier.opperation = Opperation;
	
	# Don't know what to do with this one
	def Packet0x21(self, buff):
		ChunkX = buff.readInt();
		ChunkZ = buff.readInt();
		GroundUpcontinuous = buff.readBool();	
		Primarybitmap = buff.readUnsignedByte();
		Size = buff.readVarInt();
		Data = "";
		for i in range(Size/12288):
			if Primarybitmap & (1 << i):
				for j in range(4096):
					blockID = (buff.readByte() << 8) + buff.readByte();
					metaData = BlockID & 15;
					blockID <<= 4;
					x = ChunckX+(j-(j%256)%4096);
					y = (i*16)+(j%16);
					z = ChunckZ+(j-(j%16)%256)-(j%256);
					z = position & 0x0F00;
					block = Block();
					block.location.set(x+ChunkX, y, z+ChunkZ);
					block.blockID = blockID;
					block.metaData = metaData;
					self.bot.world.blocks[(x+ChunkX, y, z+ChunkZ)] = block;
		
		
	# Multi Block Change
	def Packet0x22(self, buff):
		ChunkX = buff.readInt()
		ChunkZ = buff.readInt()
		Recordcount = buff.readVarInt()
		
		for i in range(Recordcount):
			position = buff.readShort();
			x = position & 0xF000;
			y = position & 0x00FF;
			z = position & 0x0F00;
			BlockID = buff.readVarInt();
			block = Block();
			block.location.set(x+ChunkX, y, z+ChunkZ);
			block.blockID = BlockID;
			self.bot.world.blocks[(x+ChunkX, y, z+ChunkZ)] = block;
	
	# Block Change
	def Packet0x23(self, buff):
		Location = buff.readPosition();
		BlockID = buff.readVarInt();
		
		block = Block();
		block.location = Location;
		block.blockID = BlockID;
		self.bot.world.blocks[Location.get()] = block;
		print("block: " + str(BlockID) + " - location: " + str(Location.get()));
		
	# Block Action
	def Packet0x24(self, buff):
		Location = buff.readPosition();
		Byte1 = buff.readUnsignedByte();
		Byte2 = buff.readUnsignedByte();
		BlockType = buff.readVarInt();
		
		block = self.bot.world.blocks[Location.get()];
		block.location = Location;
		block.blockType = BlockType
		block.blockAction = [Byte1, Byte2];
		self.bot.world.blocks[Location.get()] = block;
	
	def Packet0x25(self, buff):
		EntityID = buff.readVarInt();
		Location = buff.readPosition();
		DestroyStage = buff.readByte();
		
		print("EntityID: "+EntityID);
		print("Location: "+Location);
		print("DestroyStage: "+DestroyStage);
	
	def Packet0x26(self, buff):
		Skylightsent = buff.readBool()
		Chunkcolumncount = buff.readVarInt()
		for i in range(Chunkcolumncount):
			CX = buff.readInt()
			CZ = buff.readInt()
			PBitmap = buff.readShort()
			Data = buff.readUnsignedByte()
	
	def Packet0x27(self, buff):
		X = buff.readFloat()
		Y = buff.readFloat()
		Z = buff.readFloat()
		Radius = buff.readFloat()
		Recordcount = buff.readInt()
		Records = buff.readBool()
		PlayerMotionX = buff.readBool()
		PlayerMotionY = buff.readBool()
		PlayerMotionZ = buff.readBool()
	
	def Packet0x28(self, buff):
		EffectID = buff.readInt()
		Location = buff.readPosition()
		Data = buff.readInt()
		Disablerelativevolume = buff.readBool()
	
	def Packet0x29(self, buff):
		Soundname = buff.readString()
		EffectpositionX = buff.readInt()
		EffectpositionY = buff.readInt()
		EffectpositionZ = buff.readInt()
		Volume = buff.readBool()
		Pitch = buff.readUnsignedByte()
	
	def Packet0x2A(self, buff):
		ParticleId = buff.readInt()
		LongDistance = buff.readBool()
		X = buff.readFloat()
		Y = buff.readFloat()
		Z = buff.readFloat()
		OffsetX = buff.readFloat()
		OffsetY = buff.readFloat()
		OffsetZ = buff.readFloat()
		Particledata = buff.readFloat()
		Numberofparticles = buff.readInt()
		Data = [];
		# After testing, found that ParticleId 38 is recieved from falling
		if ParticleId >= 0 and ParticleId <=35:
			pass; # No data required
		else:
			print("New particle found with ID: "+str(ParticleId));
			
	
	def Packet0x2B(self, buff):
		Reason = buff.readUnsignedByte()
		Value = buff.readBool()
	
	def Packet0x2C(self, buff):
		EntityID = buff.readVarInt()
		Type = buff.readByte()
		X = buff.readInt()
		Y = buff.readInt()
		Z = buff.readInt()
	
	def Packet0x2D(self, buff):
		Windowid = buff.readUnsignedByte()
		InventoryType = buff.readString()
		Windowtitle = buff.readBool()
		NumberofSlots = buff.readUnsignedByte()
		EntityID = buff.readInt()
	
	def Packet0x2E(self, buff):
		WindowID = buff.readUnsignedByte()
	
	def Packet0x2F(self, buff):
		WindowID = buff.readByte()
		Slot = buff.readShort()
		Slotdata = buff.readSlot()
	
	def Packet0x30(self, buff):
		slots = []
		WindowID = buff.readUnsignedByte()
		Count = buff.readShort()
		while Count > 0:
			slots.append(buff.readSlot())
			Count -= 1
	
	def Packet0x31(self, buff):
		WindowID = buff.readUnsignedByte()
		Property = buff.readShort()
		Value = buff.readShort()
	
	def Packet0x32(self, buff):
		WindowID = buff.readUnsignedByte()
		Actionnumber = buff.readShort()
		Accepted = buff.readBool()
	
	def Packet0x33(self, buff):
		Location = buff.readPosition()
		Line1 = buff.readBool()
		Line2 = buff.readBool()
		Line3 = buff.readBool()
		Line4 = buff.readBool()
	
	def Packet0x34(self, buff):
		ItemDamage = buff.readVarInt()
		Scale = buff.readByte()
		Length = buff.readVarInt()
		Icons = buff.readBool()
		Columns = buff.readByte()
		Rows = buff.readByte()
		X = buff.readByte()
		Y = buff.readByte()
		Length = buff.readVarInt()
		Data = buff.readBool()
	
	def Packet0x35(self, buff):
		Location = buff.readPosition()
		Action = buff.readUnsignedByte()
		NBTData = buff.readBool()
	
	def Packet0x36(self, buff):
		Location = buff.readPosition()
	
	def Packet0x37(self, buff):
		Count = buff.readVarInt()
		while Count > 0:
			Entry = buff.readString()
			Value = buff.readVarInt()
			self.bot.stats.append({"Entry":Entry, "Value":Value})
			Count -= 1
	
	def Packet0x38(self, buff):
		'''
		Action = buff.readVarInt()
		if Action == 0:
			length = buff.readVarInt()
			UUID =  buff.readLong() + buff.readLong()
			while length > 0:
				props = []
				name = buff.readString()
				numofPro = buff.readVarInt()
				while numofPro > 0:
					prop = []
					pname = buff.readString()
					prop.append(pname)
					pvalue = buff.readString()
					prop.append(pbalue)
					isSinged = buff.readBool()
					if isSinged:
						signic = buff.readString()
						prop.append(signic)
					props.append(prop)
					numofPro -= 1
				length -= 1
				gamemode = buff.readVarInt()
				ping = buff.readVarInt()
				if buff.readBool():
					displayName = buff.readString()
					posit = buff.readByte()
		elif Action == 1:
			length = buff.readVarInt()
			UUID =  buff.readLong() + buff.readLong()
			while length > 0:
				gamemode = buff.readVarInt()
				length -= 1
		elif Action == 2:
			length = buff.readVarInt()
			UUID =  buff.readLong() + buff.readLong()
			while length > 0:
				ping = buff.readVarInt()
				length -= 1
		elif Action == 3:
			length = buff.readVarInt()
			UUID =  buff.readLong() + buff.readLong()
			while length > 0:
				hasDisplayName = buff.readBool()
				if hasDisplayName:
					displayName = buff.readString()
					posit = buff.readByte()
				length -= 1
		elif Action == 4:
			length = buff.readVarInt()
			UUID =  buff.readLong() + buff.readLong()
			print("EROROROROROR")
		Length = buff.readVarInt()
		UUID = buff.readBool()'''
		pass
	
	def Packet0x39(self, buff):
		Flags = buff.readByte()
		Flyingspeed = buff.readFloat()
		Walkingspeed = buff.readFloat()
	
	def Packet0x3A(self, buff):
		Count = buff.readVarInt()
		Match = buff.readString()
	
	def Packet0x3B(self, buff):
		Objectivename = buff.readString()
		Mode = buff.readByte()
		Objectivevalue = buff.readString()
		Type = buff.readString()
	
	def Packet0x3C(self, buff):
		Scorename = buff.readString()
		UpdateRemove = buff.readByte()
		ObjectiveName = buff.readString()
		Value = buff.readVarInt()
	
	def Packet0x3D(self, buff):
		Position = buff.readByte()
		ScoreName = buff.readString()
	
	def Packet0x3E(self, buff):
		TeamName = buff.readString()
		Mode = buff.readByte()
		TeamDisplayName = buff.readString()
		TeamPrefix = buff.readString()
		TeamSuffix = buff.readString()
		Friendlyfire = buff.readByte()
		NameTagVisibility = buff.readString()
		Color = buff.readByte()
		Playercount = buff.readVarInt()
		Players = buff.readBool()
	
	def Packet0x3F(self, buff):
		Channel = buff.readString()
		Data = buff.readString()
	def Packet0x40(self, buff):
		Reason = buff.readString()
		print("\nKicked from Server:" + Reason)
		self.bot.loggedIn = False;
		thread.interrupt_main();
	
	def Packet0x41(self, buff):
		Difficulty = buff.readUnsignedByte()
	
	def Packet0x42(self, buff):
		Event = buff.readVarInt()
		Duration = buff.readVarInt()
		EntityID = buff.readInt()
		PlayerID = buff.readVarInt()
		EntityID = buff.readInt()
		Message = buff.readString()
	
	def Packet0x43(self, buff):
		CameraID = buff.readVarInt()
	
	def Packet0x44(self, buff):
		Action = buff.readVarInt()
		if Action == 0:
			Radios = buff.readDouble()
		elif Action == 1:
			OldRadius = buff.readDouble()
			newRadius = buff.readDouble()
			speed = buff.readVarLong()
		elif Action == 2:
			x = buff.readDouble()
			z = buff.readDouble()
		elif Action == 3:
			x = buff.readDouble()
			z = buff.readDouble()
			oldRadius = buff.readDouble()
			newRadius = buff.readDouble()
			portalTeleBound = buff.readVarInt()
			warningTime = buff.readVarInt()
			warningBlocks = buff.readVarInt()
		elif Action == 4:
			warningTime = buff.readVarInt()
		elif Action == 5:
			wanringBlocks = buff.readVarInt()
	def Packet0x45(self, buff):
		Action = buff.readVarInt()
	def Packet0x46(self, buff):
		Threshold = buff.readVarInt()
		print("Got compression")
	
	def Packet0x47(self, buff):
		Header = buff.readBool()
		Footer = buff.readBool()
	
	def Packet0x48(self, buff):
		URL = buff.readString()
		Hash = buff.readString()
	
	def Packet0x49(self, buff):
		EntityID = buff.readVarInt()
		Tag = buff.readBool()
