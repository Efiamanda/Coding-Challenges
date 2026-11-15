#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cstdlib>
#include <set>
#include <algorithm>
#include <cctype>
#include <climits>

// Helper function for C++ compability
bool startsWith(const std::string& str, const std::string& prefix) {
    return str.length() >= prefix.length() &&
           str.substr(0, prefix.length()) == prefix;
}

// Configuration structure to hold all parsed options
struct CutConfig {
    std::vector<int> fields;        // -f: field numbers (1-based)
    std::vector<int> characters;    // -c: character positions (1-based)
    std::vector<int> bytes;         // -b: byte positions (1-based)
    std::string delimiter = "\t";   // -d: field delimiter
    std::string filename;           // input filename
    bool only_delimited = false;    // -s: suppress lines with no delimiter
    bool commpliment = false;       // --compliment: select complement of fields
    bool help = false;              // --help: show usage
    
    // Helper to check if any selection option is set
    bool hasSelection() const {
        return !fields.empty() || !characters.empty() || !bytes.empty();
    }
};

class ArgumentParser {
public:
    static CutConfig parse(int argc, char** argv) {
        CutConfig config;

        for (int i = 1; i < argc; i++) {
            std::string arg = argv[i];

            if (arg == "--help" || arg == "-h") {
                config.help = true;
                return config;
            }
            else if (arg == "-s" || arg == "--only-delimited") {
                config.only_delimited = true;
            }
            else if (arg == "--complement") {
                config.commpliment = true;
            }
            else if (startsWith(arg, "-f")) {
                config.fields = parseRange(extractOptionValue(arg, "-f"));
            }
            else if (startsWith(arg, "--fields=")) {
                config.fields = parseRange(extractOptionValue(arg, "--fields"));
            }
            else if (startsWith(arg, "-c")) {
                config.fields = parseRange(extractOptionValue(arg, "-c"));
            }
            else if (startsWith(arg, "--characters=")) {
                config.fields = parseRange(extractOptionValue(arg, "--characters="));
            }
            else if (startsWith(arg, "-b")) {
                config.fields = parseRange(extractOptionValue(arg, "-b"));
            }
            else if (startsWith(arg, "--bytes=")) {
                config.fields = parseRange(extractOptionValue(arg, "--bytes="));
            }
            else if (startsWith(arg, "-d")) {
                std::string delimiter_value = extractOptionValue(arg, "-d");
                if (delimiter_value.empty() && i + 1 < argc) {
                    config.delimiter = delimiter_value;
                } else {
                    throw std::runtime_error("Option -d requires an argument");
                }
            }
            else if (startsWith(arg, "--delimiter=")) {
                config.delimiter = extractOptionValue(arg, "--delimiter=");
            }
            else if (arg == "-") {
                config.filename = ""; //empty filename means stdin
            }
            else if (startsWith(arg, "-")) {
                throw std::runtime_error("Unknown option: " + arg);
            }
        }
        return config;
    }

    static void printUsage(const std::string& program_name) {
        std::cout << "Usage: " << program_name << " OPTION... [FILE]\n";
        std::cout << "Print selected parts of lines from each FILE to standard output.\n\n";
        std::cout << "Options:\n";
        std::cout << "  -f, --fields=LIST       select only these fields\n";
        std::cout << "  -c, --characters=LIST   select only these charcters\n";
        std::cout << "  -b, --bytes=LIST        select only these bytes\n";
        std::cout << "  -d, --delimiter=DELIM   use DELIM instead of TAB for field delimiter\n";
        std::cout << "  -s, --only-delimited    do not print lines not containing delimiters\n";
        std::cout << "      --complement        complement the set of selected bytes, characters\n";
        std::cout << "                          or fields\n";
        std::cout << "  -h, --help              display this help and exit\n\n";
        std::cout << "LIST is made up of one range, or many ranges separated by commas.\n";
        std::cout << "Selected input is written in the same order that it is read, and is\n";
        std::cout << "written exactly once.\n\n";
    }

private:
    // Helper function to extract option value, eliminating magic numbers
    static std::string extractOptionValue(const std::string& arg, const std::string& option) {
        if (arg.length() > option.length()) {
            return arg.substr(option.length());
        }
        return "";
    }
    static std::vector<int> parseRange(const std::string& range_str) {
        std::vector<int> result;
        std::set<int> unique_positions; // Use set to avoid duplicaates and auto-sort

        if (range_str.empty()) {
            throw std::runtime_error("Empty range specification");
        }

        std::stringstream ss(range_str);
        std::string item;

        while (std::getline(ss, item, ',')) {
            if (item.empty()) continue;

            // Check for range
            size_t dash_pos = item.find('-');
            size_t space_pos = item.find(' ');

            // Check for space with dash is not found
            if (dash_pos != std::string::npos) {
                dash_pos = space_pos;
            }

            if (dash_pos != std::string::npos) {
                std::string start_str = item.substr(0, dash_pos);
                std::string end_str = item.substr(dash_pos + 1);

                int start = start_str.empty() ? 1 : std::stoi(start_str);
                int end = end_str.empty() ? INT_MAX : std::stoi(end_str);

                if (start < 1) {
                    throw std::runtime_error("Invalid range start: " + std::to_string(start));
                }
                if (end < start && end != INT_MAX) {
                    throw std::runtime_error("Invalid range: start > end");
                }

                // Add reasonable upper limit to prevent memory issues
                int actual_end = std::min(end, 10000);
                for (int i = start; i <= actual_end; i++) {
                    unique_positions.insert(i);
                }
            } else {
                // Single number
                int pos = std::stoi(item);
                if (pos < 1) {
                    throw std::runtime_error("Invalid position: " + std::to_string(pos));
                }
                unique_positions.insert(pos);
            }
        }
        
        // Convert set to vector
        result.assign(unique_positions.begin(), unique_positions.end());
        return result;
    }
};

// Enhanced string splitting with custom delimiter
std::vector<std::string> splitString(const std::string& line, const std::string& delimiter) {
    std::vector<std::string> parts;

    if (delimiter.length() == 1) {
        // Single character delimiter - more efficient
        char delim = delimiter[0];
        size_t start = 0;

        for (size_t i = 0; i < line.size(); i++) {
            if (line[i] == delim) {
                parts.push_back(line.substr(start, i - start));
                start = i + 1;
            }
        }
        parts.push_back(line.substr(start));
    } else {
        // Multi-character delimiter
        size_t start = 0;
        size_t pos = line.find(delimiter);

        while (pos != std::string::npos) {
            parts.push_back(line.substr(start, pos - start));
            start = pos + delimiter.length();
            pos = line.find(delimiter, start);
        }
        parts.push_back(line.substr(start));
    }
    return parts;
}

// Extract selected fields from a line
std::string extractFields(const std::string& line, const CutConfig& config) {
    std::vector<std::string> parts = splitString(line, config.delimiter);
    std::vector<std::string> selected;

    // Check if line contains delimiter
    if (config.only_delimited && line.find(config.delimiter) == std::string::npos) {
        return ""; // Skip this line
    }

    for (int field_num : config.fields) {
        if (field_num <= static_cast<int>(parts.size())) {
            selected.push_back(parts[field_num - 1]); // Convert to 0-based
        }
    }

    // Join selected fields with original delimiter
    std::string result;
    for (size_t i = 0; i < selected.size(); i++) {
        if (i > 0) result += config.delimiter;
        result += selected[i];
    }
    return result;
}

// Extract selected characters from a line
std::string extractCharacters(const std::string& line, const CutConfig& config) {
    std::string result;

    for (int pos : config.characters) {
        if (pos <= static_cast<int>(line.length())) {
            result += line[pos - 1]; // Convert to 0-based
        }
    }
    return result;
}

// Process a single line based on configuration
std::string processLine(const std::string& line, const CutConfig& config) {
    if (!config.fields.empty()) {
        return extractFields(line, config);
    } else if (!config.characters.empty()) {
        return extractCharacters(line, config);
    } else if (!config.bytes.empty()) {
        // For simplicity, treating bytes same as characters
        // In a full implementation, you'd handle multi-byte characters differently
        return extractCharacters(line, config);
    }
    return line; // Fallback
}

int main(int argc, char** argv) {
    try {
        CutConfig config = ArgumentParser::parse(argc, argv);

        if (config.help) {
            ArgumentParser::printUsage(argv[0]);
            return EXIT_SUCCESS;
        }

        // Validate configuration
        if (!config.hasSelection()) {
            std::cerr << "Error: Yoiu must specify one of -f, -c, or -c\n";
            ArgumentParser::printUsage(argv[0]);
            return EXIT_FAILURE;
        }

        // Check for conflicting options
        int selection_count = 0;
        if (!config.fields.empty()) selection_count++;
        if (!config.characters.empty()) selection_count++;
        if (!config.bytes.empty()) selection_count++;

        if (selection_count > 1) {
            std::cerr << "Error: Only one type of selection allowed (-f. -c, or -b)\n";
            return EXIT_FAILURE;
        }

        // Open input file or usse stdin
        std::ifstream file;
        std::istream* input = &std::cin;

        if (!config.filename.empty()) {
            file.open(config.filename);
            if (!file.is_open()) {
                std::cerr << "Error: Cannot open file " << config.filename << "\n";
                return EXIT_FAILURE;
            }
            input = &file;
        }

         // Process each line
        std::string line;
        while (std::getline(*input, line)) {
            std::string result = processLine(line, config);

            // Only print non-empty results (handles -s option)
            if (!result.empty() || !config.only_delimited) {
                std::cout << result << '\n';
            }
        }
        return EXIT_SUCCESS;
    } catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
    return EXIT_FAILURE;
    }
}