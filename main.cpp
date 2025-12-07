#include <iostream>
#include <string>
#include <FL/Fl.H>
#include <FL/Fl_Double_Window.H>
#include <FL/Fl_Native_File_Chooser.H>
#include <FL/Fl_Text_Display.H>
#include <FL/Fl_Button.H>
#include <FL/Fl_Box.H>
#include <cstdlib>

bool support_DJVU = true;
bool support_PDF = true;
bool support_DOC = true;
bool support_EPUB = true;


Fl_Double_Window* wstart = nullptr;
Fl_Text_Display* l = nullptr;
Fl_Button* bc = nullptr;
Fl_Button* ba = nullptr;

Fl_Double_Window* wmain = nullptr;
Fl_Double_Window* wfile_browser = nullptr;
Fl_Button* b_input_files = nullptr;
Fl_Button* b_output_directory = nullptr;

int call(std::string c) {
    std::string buffer;
    buffer.append(c);
    buffer.append(" > /dev/null 2>&1");
    return system(buffer.c_str());
};

int check_dependencies() {
    int dep_count = 0;

    // Check: ddjvu --help (expected 256)
    {
        int res = call("ddjvu --help");
        if (res == 32512) {
            l->insert("Command not found: ddjvu. Make sure to install djvulibre or djvulibre-bin package\n");
        }
        else if (res == 256) dep_count++;
        else {
            std::string msg = std::string("Unexpected exitcode (") + std::to_string(res) + "), expected 256 from ddjvu --help\n";
            l->insert(msg.c_str());
        }
    }

    // Check: djvused --help (expected 2560)
    {
        int res = call("djvused --help");
        if (res == 32512) {
            l->insert("Command not found: djvused. Make sure to install djvulibre or djvulibre-bin package\n");
        }
        else if (res == 2560) dep_count++;
        else {
            std::string msg = std::string("Unexpected exitcode (") + std::to_string(res) + "), expected 2560 from djvused --help\n";
            l->insert(msg.c_str());
        }
    }

    // Check: soffice --version (expected 0)
    {
        int res = call("soffice --version");
        if (res == 32512) {
            l->insert("Command not found: soffice. Make sure to install libreoffice package\n");
        }
        else if (res == 0) dep_count++;
        else {
            std::string msg = std::string("Unexpected exitcode (") + std::to_string(res) + "), expected 0 from soffice --version\n";
            l->insert(msg.c_str());
        }
    }

    // Check: pdfimages -v (expected 0)
    {
        int res = call("pdfimages -v");
        if (res == 32512) {
            l->insert("Command not found: pdfimages. Make sure to install poppler-utils\n");
        }
        else if (res == 0) dep_count++;
        else {
            std::string msg = std::string("Unexpected exitcode (") + std::to_string(res) + "), expected 0 from pdfimages -v\n";
            l->insert(msg.c_str());
        }
    }

    return dep_count;
}

void check_deps(void* user_data) {
    const int total_deps = 4;

    l->insert("Checking dependencies...\n");
    int dep_count = check_dependencies();
    {
        std::string msg = std::string("Dependencies: ") + std::to_string(dep_count) + "/" + std::to_string(total_deps) + "\n";
        l->insert(msg.c_str());
    }
    if (dep_count < total_deps) {
        l->insert("Some dependencies were not found. Would you like to still continue?");
        bc->show();
    } else if (dep_count == 0) {
        l->insert("No dependencies found. Please install dependencies and restart in order to continue.");
    } else {
        l->insert("All dependencies found!");
        wstart->hide();
        wmain->show();
        // bc->show();
    }
}

static void ba_cb(Fl_Widget* o) {
    exit(0);
}

static void bc_cb(Fl_Widget* o) {
    wstart->hide();
    wmain->show();
}

int main(int argc, char **argv) {
    
    wstart = new Fl_Double_Window(600, 256);
    
    {
        l = new Fl_Text_Display(5, 5, 590, 196);
        Fl_Text_Buffer* buff = new Fl_Text_Buffer();
        l->buffer(buff);
        
        Fl::add_timeout(0, check_deps);
        
        bc = new Fl_Button(80, 196+10, 74, 32, "Continue");
        bc->hide();
        bc->callback((Fl_Callback0*)bc_cb);
        ba = new Fl_Button(5, 196+10, 64, 32, "Abort");
        ba->callback((Fl_Callback0*)ba_cb);
    }
    wstart->end();

    wmain = new Fl_Double_Window(512, 512);
    {
        new Fl_Box(30, 20, 200, 10, "Choose files to extract images from.");
        b_input_files = new Fl_Button(10, 40, 128, 32, "Choose.");
        new Fl_Box(30, 88, 120, 10, "Choose output directory.");
        b_output_directory = new Fl_Button(10, 108, 128, 32, "Choose.");
    }
    wmain->end();

    wstart->show(argc, argv);

    return Fl::run();
};
