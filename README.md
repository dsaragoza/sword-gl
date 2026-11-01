# sword-gl

Idiomatic, low-overhead OpenGL Core Profile bindings and binding generator for the Sword programming language. This library wraps the official Khronos OpenGL XML API Registry (`gl.xml`) to provide type-safe
OpenGL constants, runtime function pointer loading (`gl.Init`), and context-bound methods via Sword's C Foreign Function Interface (FFI).

## Dependencies

Unlike static C libraries, OpenGL functions are loaded dynamically at runtime through your graphics driver's procedure loader (such as `glfw.GetProcAddress` from
[`sword-glfw`](https://github.com/dsaragoza/sword-glfw)). You only need an active OpenGL context and a system graphics driver supporting your target OpenGL version.

*Note: Only if you wish to manually generate custom bindings from `codegen/gl.xml` is Python 3 required.*

## Setup

**sword-gl** is distributed as a standard Sword module (`github.com/dsaragoza/sword-gl`) and can be added to any Sword project with a `sword.mod` file using `shield`.

Pre-generated bindings are maintained across dedicated branches for the most common OpenGL Core targets:

| Branch | OpenGL Version | Recommended Target | Installation Command |
| :--- | :--- | :--- | :--- |
| `main` *(default)* | **OpenGL 4.6** | Modern Windows & Linux | `shield get github.com/dsaragoza/sword-gl` |
| `4.1` | **OpenGL 4.1** | macOS & Cross-Platform | `shield get github.com/dsaragoza/sword-gl@4.1` |
| `3.3` | **OpenGL 3.3** | Legacy / Broad Hardware Support | `shield get github.com/dsaragoza/sword-gl@3.3` |

**Step-by-step installation:**

1. **Initialize a Sword module** in your project directory (if you do not already have a `sword.mod` file):
    ```bash
    shield new example.com/my-app
    cd my-app
    ```
2. **Fetch and add `sword-gl` to your `sword.mod`** (optionally appending `@4.1` or `@3.3` for your target OpenGL version):
    ```bash
    shield get github.com/dsaragoza/sword-gl
    ```
3. **Import the package** in your `.sword` source files:
    ```sword
    import "github.com/dsaragoza/sword-gl"
    ```
    The package is exposed under the `gl` namespace (`gl.Init()`, `gl.GL_COLOR_BUFFER_BIT`, etc.), and OpenGL commands are invoked as methods on the loaded `gl.Context` struct (`ctx.Clear()`,
    `ctx.Viewport()`, etc., stripping the `gl` prefix).

## Quickstart

Below is a complete example pairing `sword-glfw` and `sword-gl` to create a window, load OpenGL function pointers, and clear the screen in a render loop:

```sword
import "github.com/dsaragoza/sword-glfw"
import "github.com/dsaragoza/sword-gl"

func main() int {
    if !glfw.Init() {
        return -1
    }

    glfw.WindowHint(glfw.GLFW_CONTEXT_VERSION_MAJOR, 4)
    glfw.WindowHint(glfw.GLFW_CONTEXT_VERSION_MINOR, 6)
    glfw.WindowHint(glfw.GLFW_OPENGL_PROFILE, glfw.GLFW_OPENGL_CORE_PROFILE)

    mut window := glfw.CreateWindow(640, 480, "Hello, OpenGL!", nil, nil) catch {
        glfw.Terminate()
        return -1
    }

    glfw.MakeContextCurrent(window)

    // Load OpenGL function pointers after making the context current
    mut glCtx := gl.Init(glfw.GetProcAddress) catch {
        glfw.DestroyWindow(window)
        glfw.Terminate()
        return -1
    }

    for {
        if glfw.WindowShouldClose(window) {
            break
        }

        glCtx.ClearColor(0.1, 0.2, 0.3, 1.0)
        glCtx.Clear(gl.GL_COLOR_BUFFER_BIT)

        glfw.SwapBuffers(window)
        glfw.PollEvents()
    }

    glfw.DestroyWindow(window)
    glfw.Terminate()
    return 0
}
```

Compile and run your	project with:
```bash
shield . -o app
./app
```

## Custom Binding Generation

If you need bindings for a specific OpenGL version (from `1.0` to `4.6`) not covered by the pre-generated branches, you can use the included code generator in [`codegen/generator.py`](codegen/generator.py):

```bash
# Generate bindings by target platform (windows/linux -> 4.6, macos -> 4.1)
python3 codegen/generator.py -p linux -f gl.sword

# Or generate bindings for an explicit OpenGL version (1.0 through 4.6)
python3 codegen/generator.py -v 3.3 -f gl.sword
```

### CLI Options

| Flag | Long Flag | Description |
| :--- | :--- | :--- |
| `-f` | `--file` | **(Required)** Output path for the generated `.sword` bindings file. |
| `-p` | `--platform` | Target platform (`windows`, `linux`, `macos`). Mutually exclusive with `-v`. |
| `-v` | `--version` | Target OpenGL version (`1.0` to `4.6`). Mutually exclusive with `-p`. |
