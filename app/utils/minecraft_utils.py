#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Minecraft-specific utility functions.
"""

import os
import requests
import logging
from uuid import UUID
from io import BytesIO
from PyQt6.QtGui import QPixmap

def get_player_head(username=None, uuid=None, size=64):
    """
    Get the player's head avatar as a QPixmap.
    
    Args:
        username: Minecraft username (optional if uuid is provided)
        uuid: Player UUID string or UUID object (optional if username is provided)
        size: Size of the returned avatar in pixels
        
    Returns:
        QPixmap with the player head or None if failed
    """
    try:
        # If we have a username but no UUID, fetch the UUID first
        if username and not uuid:
            response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}")
            if response.status_code == 200:
                data = response.json()
                uuid = data.get('id')
            else:
                logging.warning(f"Failed to get UUID for username {username}: {response.status_code}")
                return None
        
        # Convert UUID string to proper format if needed
        if isinstance(uuid, str):
            uuid = uuid.replace('-', '')
            uuid = str(UUID(uuid))
        
        # Fetch the avatar from Crafatar
        #add uuid back to the url
        url = f"https://crafatar.com/avatars/de4e63b1-61da-4591-9224-23f75bf6102f?size={size}&overlay=true"
        response = requests.get(url)
        if response.status_code == 200:
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            return pixmap
        else:
            logging.warning(f"Failed to fetch avatar from Crafatar: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching player head: {e}")
        return None