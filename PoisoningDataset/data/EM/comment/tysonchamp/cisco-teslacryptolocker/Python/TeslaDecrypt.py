'''
 *  Copyright (C) 2015 Cisco Talos Security Intelligence and Research Group
 *
 *  Authors: Emmanuel Tacheau and Andrea Allievi
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License version 2 as
 *  published by the Free Software Foundation.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 *  MA 02110-1301, USA.
 * 
 *	Filename: TeslaDeCrypt.py
 *	This module will perform AES decryption for file encrypted with
 *      the ransomware TeslaCrypt
 *
 *      Usage:   python TeslaDecrypt.py --file file_encrypted.ecc --key master_key
 *               The result will produce a file named file_encrypted.dec using AES 256 CBC mode
 *
 *               Encrypted files are defined as follow:
 *               First 16 bytes are containing IV
 *               Then with 4 bytes is the length of the file
 *               Then the encrypted data
 *
 *	Last revision: 04/17/2015
 *
'''