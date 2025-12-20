cmake_minimum_required(VERSION 3.16)
project(dream-team-desktop VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt configuration
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Find Qt6 packages
find_package(Qt6 REQUIRED COMPONENTS
    Core
    Widgets
    Network
    Charts
)

# Configure defaults
set(TEXT_API_URL_DEFAULT "http://localhost:8000")
set(CHAT_API_URL_DEFAULT "http://localhost:8000")
set(ANALYTICS_API_URL_DEFAULT "http://localhost:8000")

if(DEFINED TEXT_API_URL AND NOT "${TEXT_API_URL}" STREQUAL "")
    set(TEXT_API_URL_DEFAULT "${TEXT_API_URL}")
elseif(DEFINED ENV{TEXT_SERVICE_A_DOMAIN} AND NOT "$ENV{TEXT_SERVICE_A_DOMAIN}" STREQUAL "")
    set(TEXT_API_URL_DEFAULT "https://$ENV{TEXT_SERVICE_A_DOMAIN}")
endif()

if(DEFINED CHAT_API_URL AND NOT "${CHAT_API_URL}" STREQUAL "")
    set(CHAT_API_URL_DEFAULT "${CHAT_API_URL}")
elseif(DEFINED ENV{CHAT_SERVICE_DOMAIN} AND NOT "$ENV{CHAT_SERVICE_DOMAIN}" STREQUAL "")
    set(CHAT_API_URL_DEFAULT "https://$ENV{CHAT_SERVICE_DOMAIN}")
endif()

if(DEFINED ANALYTICS_API_URL AND NOT "${ANALYTICS_API_URL}" STREQUAL "")
    set(ANALYTICS_API_URL_DEFAULT "${ANALYTICS_API_URL}")
elseif(DEFINED ENV{ANALYTICS_SERVICE_DOMAIN} AND NOT "$ENV{ANALYTICS_SERVICE_DOMAIN}" STREQUAL "")
    set(ANALYTICS_API_URL_DEFAULT "https://$ENV{ANALYTICS_SERVICE_DOMAIN}")
endif()

configure_file(
    src/app_config.h.in
    ${CMAKE_CURRENT_BINARY_DIR}/generated_config.h
    @ONLY
)

# Source files
set(SOURCES
    src/app_config.cpp
    src/api_client.cpp
    src/analytics_window.cpp
    src/chat_window.cpp
    src/document_window.cpp
    src/edits_window.cpp
    src/init_document_window.cpp
    src/main.cpp
    src/main_window.cpp
    src/navigation_bar.cpp
    src/settings_window.cpp
    src/window_manager.cpp
)

set(HEADERS
    src/app_config.h
    src/api_client.h
    src/analytics_window.h
    src/chat_window.h
    src/document_window.h
    src/edits_window.h
    src/init_document_window.h
    src/main_window.h
    src/navigation_bar.h
    src/session_state.h
    src/settings_window.h
    src/window_manager.h
)

# Create executable
add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})

# Link Qt libraries
target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt6::Core
    Qt6::Widgets
    Qt6::Network
    Qt6::Charts
)

target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_BINARY_DIR})

# Set output directory
set_target_properties(${PROJECT_NAME} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Installation rules
install(TARGETS ${PROJECT_NAME}
    RUNTIME DESTINATION bin
)
