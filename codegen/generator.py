import argparse
import xml.etree.ElementTree as ET

TARGET_VERSION = 4.6

SWORD_TYPES_CONVERSION_TABLE = {
    "void": "void",
    "GLbyte": "i8",
    "GLboolean": "u8",
    "GLenum": "u32",
    "GLhandleARB": "u32",
    "GLsync": "?[*]u8",
    "GLint": "i32",
    "GLsizei": "i32",
    "GLuint64": "u64",
    "GLuint": "u32",
    "GLshort": "i16",
    "GLushort": "u16",
    "GLubyte": "u8",
    "GLfloat": "f32",
    "GLdouble": "f64",
    "GLintptr": "i64",
    "GLsizeiptr": "i64",
    "GLbitfield": "u32",
    "GLvdpauSurfaceNV": "i64",
    "GLVULKANPROCNV": "i64",
    "void *": "?[*]u8",
    "void **": "?[*][*]u8",
    "GLboolean *": "?*u8",
    "GLchar *": "?*u8",
    "GLenum *": "?*u32",
    "GLuint *": "?*u32",
    "GLushort *": "?*u16",
    "GLint *": "?*i32",
    "GLubyte *": "?*u8",
    "GLsizei *": "?*i32",
    "GLuint64 *": "?*u64",
    "GLint64 *": "?*i64",
    "GLfloat *": "?*f32",
    "GLdouble *": "?*f64",
    "const void *const*": "?[*][*]u8",
    "const GLboolean *": "?*u8",
    "const GLenum *": "?*u32",
    "const GLbyte *": "?*i8",
    "const GLubyte *": "?*u8",
    "const GLchar *": "?[*]u8",
    "const GLchar *const*": "?[*][*]u8",
    "const GLuint *": "?*u32",
    "const GLushort *": "?*u16",
    "const GLshort *": "?*i16",
    "const GLsizei *": "?*i32",
    "const GLintptr *": "?*i64",
    "const GLsizeiptr *": "?*i64",
    "const void *": "?[*]u8",
    "const GLfloat *": "?*f32",
    "const GLdouble *": "?*f64",
    "const GLint *": "?*i32",
    "GLDEBUGPROC": "?[*]u8"
}

SWORD_KEYWORDS_CONVERSION_TABLE = {
    "func": "fun",
    "type": "t",
    "in": "input",
    "string": "str"
}

def parse_active_enums_and_commands(root) -> (set, set):
    # Parse all feature tags with api equal to gl, excluding gles1, gles2 and glsc2, and with version equal to the target version. 
    active_enums    = set()
    active_commands = set()
    for feature in root.iter("feature"):
        attrib = feature.attrib
        if attrib["api"] != "gl" or float(attrib["number"]) > TARGET_VERSION:
            continue

        # For each require tag, iter over all enums and commands, adding them to the corresponding sets 
        for require in feature.iter("require"):
            for enum in require.iter("enum"):
                attrib = enum.attrib
                active_enums.add(attrib["name"])
            
            for command in require.iter("command"):
                attrib = command.attrib
                active_commands.add(attrib["name"])

        # For each core profile remove tag, iter over all enums and commands, removing them from the corresponding sets
        for remove in feature.iter("remove"):
            attrib = remove.attrib
            if attrib["profile"] == "core":
                for enum in remove.iter("enum"):
                    attrib = enum.attrib
                    active_enums.discard(attrib["name"])

                for command in remove.iter("command"):
                    attrib = command.attrib
                    active_commands.discard(attrib["name"])
                
    return (active_enums, active_commands)

def parse_and_translate_enums(root, enums) -> dict:
    enums_translated = {}
    for _enums in root.iter("enums"):
        for enum in _enums.iter("enum"):
            enum_name = enum.attrib["name"]
            if enum_name not in enums:
                continue

            enum_value = enum.attrib["value"]
            enums_translated[enum_name] = enum_value

    return enums_translated

def parse_and_translate_commands(root, commands) -> dict:
    # Parse all commands inside the <commands> tag, extracting and translating names, return types and arguments and its types to Sword equivalents
    commands_translated = {}
    for _commands in root.iter("commands"):
        for command in _commands.iter("command"):
            # Parse the <proto> tag (return type and function name)
            proto = command.find("proto")
            
            # Only translate the command if it is in the set of active commands
            name = proto.find("name").text 
            if name not in commands:
                continue
            commands_translated[name] = {
                "params": {}
            }

            return_type = proto.text if proto.text is not None else "" 
            ptype = proto.find("ptype")
            if ptype is not None:
                return_type += ptype.text + ptype.tail
            return_type = " ".join(return_type.split())
            
            # Do not continue if found type is not yet implemented
            if return_type not in SWORD_TYPES_CONVERSION_TABLE.keys():
                print(f"OpenGL type not translated: {return_type}\nExiting program...")
                exit(0)

            # Translate the type to a Sword equivalent
            sword_type = SWORD_TYPES_CONVERSION_TABLE[return_type]
            commands_translated[name]["return"] = sword_type

            # Parse the command parameters names and types
            for param in command.iter("param"):
                 param_name = param.find("name").text
                 
                 param_type = param.text if param.text is not None else "" 
                 ptype = param.find("ptype")
                 if ptype is not None:
                     param_type += ptype.text + ptype.tail
                 param_type = " ".join(param_type.split())

                 # Do not continue if found type is not yet implemented
                 if param_type not in SWORD_TYPES_CONVERSION_TABLE.keys():
                     print(f"OpenGL type not translated: {param_type}\nExiting program...")
                     exit(0)
                 param_sword_type = SWORD_TYPES_CONVERSION_TABLE[param_type]

                 commands_translated[name]["params"][param_name] = param_sword_type
    
    return commands_translated

def emit_sword_code(enums, commands) -> str:
    # Package definition
    code = "package gl\n"

    # Constants definition
    code += "\n// OpenGL enums definitions\n"
    for enum in enums.keys():
        value = enums[enum]
        code += f"const {enum} = {value}\n"

    # OpenGL function pointers definition withing a context struct
    code += "\n// OpenGL function pointers definitions\n"
    code += "struct Context {\n"
    for command in commands.keys():
        params = commands[command]["params"]
        return_type = commands[command]["return"]

        # Construct the command parameters code
        param_code = ""
        for param, param_type in params.items():
            # Transform reserved keywords
            param_name = param
            if param_name in SWORD_KEYWORDS_CONVERSION_TABLE.keys():
                param_name = SWORD_KEYWORDS_CONVERSION_TABLE[param]

            param_code += f"{param_type}, "
        
        if len(param_code) > 0:
            param_code = param_code[:-2]

        code += f"\t{command} ?[*]u8\n"
    code += "}\n"

    # Idiomatic OpenGL to Sword function calls
    code += "\n// Idiomatic OpenGL to Sword function calls definitions\n"
    for command in commands.keys():
        params = commands[command]["params"]
        return_type = commands[command]["return"]

        # Construct the command parameters and types code
        param_code = ""
        param_types_code = ""
        for param, param_type in params.items():
            # Transform reserved keywords
            param_name = param
            if param_name in SWORD_KEYWORDS_CONVERSION_TABLE.keys():
                param_name = SWORD_KEYWORDS_CONVERSION_TABLE[param]

            param_code += f"{param_name} {param_type}, "
            param_types_code += f"{param_type}, "
        
        if len(param_code) > 0:
            param_code = param_code[:-2]
            param_types_code = param_types_code[:-2]

        # Construct the parameters call code
        param_call_code = ""
        for param, param_type in params.items():
            # Transform reserved keywords
            param_name = param
            if param_name in SWORD_KEYWORDS_CONVERSION_TABLE.keys():
                param_name = SWORD_KEYWORDS_CONVERSION_TABLE[param]

            param_call_code += f"{param_name}, "
        
        if len(param_code) > 0:
            param_call_code = param_call_code[:-2]

        code += f"""
func (c *Context) {command[2:]}({param_code}) {return_type} {{
    if command := c.{command} {{
        fn := extern func({param_types_code}) {return_type}(command)
        {"return " if return_type != "void" else ""}fn({param_call_code})
    }}
    {"return nil" if "?" in return_type else ("return 0" if return_type != "void" else "")}
}}
        """

    # Construct the load function
    code += f"\n// OpenGL function pointers load function [SHOULD BE CALLED BEFORE ANY OTHER OPENGL FUNCTION]\n"
    code += f"""error openGLCommandNotFound = "OpenGL command not found. Check your driver version and/or your system supported features."

func Init(procLoader extern func([*]u8) ?[*]u8) !Context {{
    mut c := Context{{
{"".join(("\t\t" + command + ": nil,\n") for command in commands.keys())}
    }}

    mut commandName := ""

{"".join(('\tcommandName = "'  + command + '\x00"\n\tc.' + command + " = procLoader(commandName.ptr) orelse return error.openGLCommandNotFound\n\n") for command in commands.keys()) }
    return c
}}
    """

    return code

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-p", "--platform", choices = ["windows", "macos", "linux"], help = "The target platform for which to generate the bindings.", required = True)
    arg_parser.add_argument("-v", "--version", type = float, choices = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 2.0, 2.1, 3.0, 3.1, 3.2, 3.3, 4.0, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6], help = "The target OpenGL version for which to generate the bindings.")
    arg_parser.add_argument("-f", "--file", help = "The target sword file to output the generated bindings.", required = True)
    args = arg_parser.parse_args()

    # Check the chosen platform, switching the target version
    # If the target version arg is passed, ignore the platform
    if args.version is None:
        if "windows" == args.platform or "linux" == args.platform:
            TARGET_VERSION = 4.6
        else:
            TARGET_VERSION = 4.1
    else:
        TARGET_VERSION = args.version

    tree = ET.parse("codegen/gl.xml")
    root = tree.getroot()

    # Generate the bindings by parsing the gl.xml file
    active_enums, active_commands = parse_active_enums_and_commands(root)
    print(f"Active enumerations: {len(active_enums)} | Active commands: {len(active_commands)}")

    enums_translated = parse_and_translate_enums(root, active_enums)
    print(f"Translated enums: {len(enums_translated.keys())}")

    commands_translated = parse_and_translate_commands(root, active_commands)
    print(f"Translated commands: {len(commands_translated.keys())}")
   
    # Output to provided file
    with open(args.file, "w") as f:
        print(emit_sword_code(enums_translated, commands_translated), file = f)
