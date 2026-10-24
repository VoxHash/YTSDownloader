plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "dev.voxhash.ytscompanion"
    // Use packages already present under ANDROID_HOME (often root-owned /opt).
    compileSdk = 36
    buildToolsVersion = "35.0.0"

    defaultConfig {
        applicationId = "dev.voxhash.ytscompanion"
        minSdk = 26
        targetSdk = 35
        versionCode = 7
        versionName = "0.11.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "COMPANION_SOURCE", "\"android-companion\"")
        ndk {
            // Chaquopy Python 3.12+: 64-bit only. Pixel 7 Pro + Quest 3 are arm64-v8a.
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    flavorDimensions += "device"
    productFlavors {
        create("phone") {
            dimension = "device"
            // GrapheneOS / phone companion (default sideload path).
        }
        create("quest") {
            dimension = "device"
            // Stable id (no .debug suffix) — Horizon OS is picky about panel package identity.
            applicationId = "dev.voxhash.ytscompanion.quest"
            buildConfigField("String", "COMPANION_SOURCE", "\"quest-companion\"")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

chaquopy {
    defaultConfig {
        version = "3.12"
        // Prefer CHAQUOPY_PYTHON, then common python3.12 locations (fish-safe builds).
        val py =
            sequenceOf(
                System.getenv("CHAQUOPY_PYTHON"),
                "/home/raider/.local/bin/python3.12",
                "/usr/bin/python3.12",
            ).firstOrNull { !it.isNullOrBlank() && file(it!!).exists() }
                ?: "python3.12"
        buildPython(py)
        pip {
            // Pin to the same yt-dlp line the desktop Suite uses in this checkout.
            install("yt-dlp==2026.10.21")
        }
    }
}

// Quest keeps a fixed applicationId across debug/release (Horizon panel + ADB scripts).
androidComponents {
    onVariants(selector().withFlavor("device" to "quest")) { variant ->
        variant.applicationId.set("dev.voxhash.ytscompanion.quest")
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.2.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.documentfile:documentfile:1.0.1")
}
