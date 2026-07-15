import sys
import threading
import webbrowser
import time

def main():
    print("=======================================================")
    print("         VISION CLIPPER STUDIO SERVER STARTER")
    print("=======================================================")
    print("\nStarting the AI Engine...\n")
    
    # Import app here so that if the package is installed globally, 
    # it finds vision_clipper.app
    from vision_clipper.app import app

    def open_browser():
        time.sleep(1.5)
        print("Server is now running!")
        print("Opening Web Dashboard in your default browser...")
        webbrowser.open("http://localhost:5000")
        print("\n=======================================================")
        print("[SUCCESS] You can now safely close this window to stop the server.")
        print("Or click the red 'Shut Down' button at the bottom of the Web Dashboard.")
        print("=======================================================\n")

    # Start the browser thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run the Flask app
    # Disable reloader because it breaks when run inside a console script
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
