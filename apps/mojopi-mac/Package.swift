// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "mojopi-mac",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "mojopi-mac", targets: ["mojopi-mac"]),
    ],
    targets: [
        .executableTarget(
            name: "mojopi-mac",
            path: "mojopi-mac",
            exclude: ["Info.plist"]
        ),
    ]
)
