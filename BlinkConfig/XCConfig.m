//////////////////////////////////////////////////////////////////////////////////
//
// B L I N K
//
// Copyright (C) 2016-2019 Blink Mobile Shell Project
//
// This file is part of Blink.
//
// Blink is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Blink is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Blink. If not, see <http://www.gnu.org/licenses/>.
//
// In addition, Blink is also subject to certain additional terms under
// GNU GPL version 3 section 7.
//
// You should have received a copy of these additional terms immediately
// following the terms and conditions of the GNU General Public License
// which accompanied the Blink Source Code. If not, see
// <http://www.github.com/blinksh/blink>.
//
////////////////////////////////////////////////////////////////////////////////


#import "XCConfig.h"

@implementation XCConfig

+ (NSString *)_valueForKey:(NSString *)key {
  NSBundle *bundle = [NSBundle bundleForClass:[XCConfig self]];
  id value = [bundle objectForInfoDictionaryKey:key];
  if (![value isKindOfClass:[NSString class]]) {
    return @"";
  }

  NSString *string = [(NSString *)value stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];

  // Xcode may leave undefined build settings as literal placeholders in processed Info.plists.
  if (([string hasPrefix:@"$("] && [string hasSuffix:@")"]) ||
      ([string hasPrefix:@"${"] && [string hasSuffix:@"}"])) {
    return @"";
  }

  return string;
}

+ (NSString *) infoPlistRevCatPubliKey {
  return [self _valueForKey:@"BLINK_REVCAT_PUBKEY"];
}

+ (NSString *) infoPlistWhatsNewURL {
  return [self _valueForKey:@"BLINK_WHATS_NEW_URL"];
}

+ (NSString *) infoPlistWhatsNewGithubURL {
  return [self _valueForKey:@"BLINK_WHATS_NEW_GITHUB_URL"];
}

+ (NSString *) infoPlistConversionOpportunityURL {
  return [self _valueForKey:@"BLINK_CONVERSION_OPPORTUNITY_URL"];
}

+ (NSString *) infoPlistKeyChainID1 {
  return [self _valueForKey:@"BLINK_KEYCHAIN_ID1"];
}

+ (NSString *) infoPlistCloudID {
  return [self _valueForKey:@"BLINK_CLOUD_ID"];
}

+ (NSString *) infoPlistFullCloudID {
  NSString *cloudID = [self infoPlistCloudID];
  return cloudID.length > 0 ? [NSString stringWithFormat:@"iCloud.%@", cloudID] : @"";
}

+ (NSString *) infoPlistGroupID {
  return [self _valueForKey:@"BLINK_GROUP_ID"];
}

+ (NSString *) infoPlistFullGroupID {
  NSString *groupID = [self infoPlistGroupID];
  return groupID.length > 0 ? [NSString stringWithFormat:@"group.%@", groupID] : @"";
}


@end
