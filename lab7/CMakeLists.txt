cmake_minimum_required(VERSION 3.22)

#
# This file is generated only once,
# and is not re-generated if converter is called multiple times.
#
# User is free to modify the file as much as necessary
#

# Setup compiler settings
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)


# Define the build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Debug")
endif()

# Set the project name
set(CMAKE_PROJECT_NAME lab7)

# Enable compile command to ease indexing with e.g. clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)

# Core project settings
project(${CMAKE_PROJECT_NAME})
message("Build type: " ${CMAKE_BUILD_TYPE})

# Enable CMake support for ASM and C languages
enable_language(C ASM)

# Create an executable object type
add_executable(${CMAKE_PROJECT_NAME})

# Add STM32CubeMX generated sources
add_subdirectory(cmake/stm32cubemx)

# Link directories setup
target_link_directories(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined library search paths
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/CMSIS-DSP/Lib
)

# Add sources to executable
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user sources here
    ${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/math_helper.c
    ${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/arm_fir_data.c 
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/BSP/B-L475E-IOT01/stm32l475e_iot01.c
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/BSP/B-L475E-IOT01/stm32l475e_iot01_accelero.c
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/BSP/Components/lsm6dsl/lsm6dsl.c
)

# Add include paths
target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined include paths
    # C:/Users/pig90/STM32CubeL4/Drivers/CMSIS/DSP/Include
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/CMSIS-DSP/Include
    ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/BSP/B-L475E-IOT01
    # ${CMAKE_CURRENT_SOURCE_DIR}/ThirdParty/BSP/Components/lsm6dsl
)

# Add project symbols (macros)
target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined symbols
)

# Remove wrong libob.a library dependency when using cpp files
list(REMOVE_ITEM CMAKE_C_IMPLICIT_LINK_LIBRARIES ob)

# Add linked libraries
target_link_libraries(${CMAKE_PROJECT_NAME}
    stm32cubemx

    # Add user defined libraries
    arm_cortexM4lf_math
)

target_link_options(${CMAKE_PROJECT_NAME} PRIVATE -u _printf_float)